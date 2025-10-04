from fastmcp import FastMCP
import os
import sqlite3


#Path to the database
BD_PATH = os.path.join(os.path.dirname(__file__), "expense-tracker.db")

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
def add_expense(date : str, name : str, amount : float, category : str, subcategory : str = '', note : str = '') -> None:
    """Adds an expense to the database."""
    with sqlite3.connect(BD_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO expenses (date, name, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?, ?)", (date, name, amount, category, subcategory, note))
        
        return {"status": "OK", "id": c.lastrowid}



@mcp.tool()
def list_expenses() -> list[dict]:
    """Returns a list of all expenses."""
    with sqlite3.connect(BD_PATH) as c:
        cur = c.execute("SELECT id, date, name, amount, category, subcategory, note FROM expenses ORDER BY ID ASC")

    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


@mcp.tool()
def delete_expense(id : int) -> None:
    """Deletes an expense from the database."""
    with sqlite3.connect(BD_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        conn.commit()


@mcp.tool()
def update_expense(id : int, date : str, name : str, amount : float, category : str, subcategory : str = '', note : str = '') -> None:
    """Updates an expense in the database."""
    with sqlite3.connect(BD_PATH) as conn:
        c = conn.cursor()
        c.execute("UPDATE expenses SET date = ?, name = ?, amount = ?, category = ?, subcategory = ?, note = ? WHERE id = ?", (date, name, amount, category, subcategory, note, id))
        conn.commit()
        return {"status": "OK"}
        
@mcp.tool()
def summarize_expenses(start_date : str, end_date : str) -> str:
    """Summarize expenses by category within an inclusive date range."""
    with sqlite3.connect(BD_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT category, SUM(amount) FROM expenses WHERE date BETWEEN ? AND ? GROUP BY category", (start_date, end_date))
        results = c.fetchall()

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
