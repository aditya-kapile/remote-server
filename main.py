
from fastmcp import FastMCP
import os
import sqlite3
import anyio



# Database path selection: prefer a writable temp dir in cloud or read-only environments
_DEF_CODE_DIR = os.path.dirname(__file__)

def _first_writable_dir(candidates: list[str]) -> str:
    for d in candidates:
        if not d:
            continue
        try:
            os.makedirs(d, exist_ok=True)
            test_path = os.path.join(d, ".write-test")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_path)
            return d
        except Exception:
            continue
    return _DEF_CODE_DIR  # last resort

# Candidate dirs: env-provided temps, /tmp, working dir 'data', then code dir
_candidates = [
    os.getenv("TMPDIR"), os.getenv("TMP"), os.getenv("TEMP"),
    "/tmp",
    os.path.join(os.getcwd(), "data"),
    _DEF_CODE_DIR,
]
_DB_DIR = _first_writable_dir(_candidates)
BD_PATH = os.path.join(_DB_DIR, "expense-tracker.db")


#Create a FastMCP server instance
mcp = FastMCP(name = "expense-tracker")

def init_db():
    """Initializes the database."""
    with sqlite3.connect(BD_PATH) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS expenses (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT NOT NULL ,
                  name TEXT  NOT NULL ,
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  subcategory TEXT DEFAULT '',
                  note TEXT DEFAULT ''
                  )
                  """)
        conn.commit()


init_db()  #calling above function to Initialize the database
@mcp.tool()
async def get_db_info() -> dict:
    """Diagnostics: returns DB path and writability info to debug read-only issues."""
    def _probe():
        info = {
            "BD_PATH": BD_PATH,
            "DB_DIR": os.path.dirname(BD_PATH),
            "exists": os.path.exists(BD_PATH),
            "dir_writable": os.access(os.path.dirname(BD_PATH), os.W_OK),
            "file_writable": os.access(BD_PATH, os.W_OK) if os.path.exists(BD_PATH) else None,
            "env": {
                "FASTMCP_CLOUD": os.getenv("FASTMCP_CLOUD"),
                "TMPDIR": os.getenv("TMPDIR"),
                "TMP": os.getenv("TMP"),
                "TEMP": os.getenv("TEMP"),
            },
        }
        # Try writing a small temp file in DB directory
        try:
            test_path = os.path.join(os.path.dirname(BD_PATH), ".write-test")
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(test_path)
            info["can_write_dir"] = True
        except Exception as e:
            info["can_write_dir"] = False
            info["write_error"] = str(e)
        return info
    return await anyio.to_thread.run_sync(_probe)


@mcp.tool()
async def add_expense(date: str, name: str, amount: float, category: str, subcategory: str = '', note: str = '') -> dict:
    """Adds an expense to the database."""
    def _op():
        with sqlite3.connect(BD_PATH) as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO expenses (date, name, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?, ?)",
                (date, name, amount, category, subcategory, note),
            )
            conn.commit()
            return {"status": "OK", "id": c.lastrowid}
    return await anyio.to_thread.run_sync(_op)



@mcp.tool()
async def list_expenses(subcategory: str = '', note: str = '') -> list[dict]:
    def _op():
        with sqlite3.connect(BD_PATH) as conn:
            base = "SELECT id, date, name, amount, category, subcategory, note FROM expenses"
            clauses, params = [], []
            if subcategory:
                clauses.append("subcategory = ?"); params.append(subcategory)
            if note:
                clauses.append("note LIKE ?"); params.append(f"%{note}%")
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            cur = conn.execute(base + where + " ORDER BY id ASC", params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    return await anyio.to_thread.run_sync(_op)


@mcp.tool()
async def delete_expense(id: int) -> None:
    """Deletes an expense from the database."""
    def _op():
        with sqlite3.connect(BD_PATH) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM expenses WHERE id = ?", (id,))
            conn.commit()
    await anyio.to_thread.run_sync(_op)


@mcp.tool()
async def update_expense(id: int, date: str, name: str, amount: float, category: str, subcategory: str = '', note: str = '') -> dict:
    """Updates an expense in the database."""
    def _op():
        with sqlite3.connect(BD_PATH) as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE expenses SET date = ?, name = ?, amount = ?, category = ?, subcategory = ?, note = ? WHERE id = ?",
                (date, name, amount, category, subcategory, note, id),
            )
            conn.commit()
            return {"status": "OK"}
    return await anyio.to_thread.run_sync(_op)

@mcp.tool()
async def summarize_expenses(start_date: str, end_date: str) -> str:
    """Summarize expenses by category within an inclusive date range."""
    def _fetch():
        with sqlite3.connect(BD_PATH) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT category, SUM(amount) FROM expenses WHERE date BETWEEN ? AND ? GROUP BY category",
                (start_date, end_date),
            )
            return c.fetchall()

    results = await anyio.to_thread.run_sync(_fetch)

    # Format results as a readable string
    if not results:
        return "No expenses found in the specified date range."

    summary = f"Expense Summary ({start_date} to {end_date}):\n"
    summary += "-" * 50 + "\n"
    total = 0
    for category, amount in results:
        summary += f"{category}: ${amount:.2f}\n"
        total += amount
    summary += "-" * 50 + "\n"
    summary += f"Total: ${total:.2f}"

    return summary



if __name__ == "__main__":
    # mcp.run()   #command to run the server  : for local server
    mcp.run(transport="http", host="0.0.0.0" , port=8000)



