from fastmcp import FastMCP
import os
import sqlite3
import anyio



# Database path with cloud fallback to writable tmp
_DB_DIR = os.getenv("TMPDIR", "/tmp") if os.getenv("FASTMCP_CLOUD") else os.path.dirname(__file__)
os.makedirs(_DB_DIR, exist_ok=True)
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
async def list_expenses() -> list[dict]:
    """Returns a list of all expenses."""
    def _op():
        with sqlite3.connect(BD_PATH) as conn:
            cur = conn.execute("SELECT id, date, name, amount, category, subcategory, note FROM expenses ORDER BY id ASC")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
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
