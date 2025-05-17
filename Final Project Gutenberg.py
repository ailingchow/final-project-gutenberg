"""
Gutenberg Book Searcher and Word Frequency Tool
Author: Ailing Chow
Date: May 16, 2025

This program provides a GUI for searching and analyzing word frequencies in books
from Project Gutenberg. It stores the results in a local SQLite3 database and returns
previously saved books.
"""

import tkinter as tk  # GUI library
from tkinter import messagebox  # For showing error popups
import urllib.request  # For downloading content from the web
import sqlite3  # For creating and managing the database
import re  # For processing and cleaning up text
from collections import Counter  # For counting word frequency
from bs4 import BeautifulSoup  # For parsing HTML pages

# Define the name of the SQLite database file
DB_NAME = "book.db"

# Database setup
def init_db():
    """Create the 'books' and 'word_frequencies' tables in the database"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            title TEXT PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS word_frequencies (
            book_title TEXT,
            word TEXT,
            frequency INTEGER,
            FOREIGN KEY(book_title) REFERENCES books(title)
        )
    ''')
    conn.commit()
    conn.close()

# Text processing function
def get_top_words(text, n=10):
    """Returns the top most frequent words."""
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    return Counter(words).most_common(n)

# Extract plain text file link and book title from a Project Gutenberg book page
def get_text_url_and_title(book_url):
    """Given a Project Gutenberg HTML book page, extract the title and plain text file URL."""
    try:
        with urllib.request.urlopen(book_url) as response:
            html = response.read()
            soup = BeautifulSoup(html, 'html.parser')

            title_tag = soup.find('h1', itemprop='name')
            title = title_tag.text.strip() if title_tag else "Unknown Title"

            link_tag = soup.find('a', string=re.compile("Plain Text UTF-8", re.I))
            if not link_tag:
                raise Exception("Plain text file not found on page.")

            text_url = urllib.request.urljoin(book_url, link_tag['href'])
            return text_url, title

    except Exception as e:
        raise Exception(f"Failed to extract text URL and title: {e}")

# GUI
class BookSearchApp:
    def __init__(self, root):
        """Initializes the GUI"""
        self.root = root
        self.root.title("Gutenberg Book Search")

        # Create GUI elements
        self.title_label = tk.Label(root, text="Search by Book Title:")
        self.title_entry = tk.Entry(root, width=50)
        self.search_button = tk.Button(root, text="Search Local DB", command=self.search_local)

        self.url_label = tk.Label(root, text="Add Book by Gutenberg URL:")
        self.url_entry = tk.Entry(root, width=50)
        self.url_button = tk.Button(root, text="Download and Store", command=self.search_url)

        self.result_text = tk.Text(root, height=15, width=60)

        # Layout the GUI elements
        self.title_label.pack()
        self.title_entry.pack()
        self.search_button.pack()
        self.url_label.pack()
        self.url_entry.pack()
        self.url_button.pack()
        self.result_text.pack()

    def search_local(self):
        """Searches the local database by book title and displays its most frequent words."""
        search_input = self.title_entry.get().strip().lower()
        if not search_input:
            messagebox.showerror("Input Error", "Please enter a book title.")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM books")
        all_titles = cursor.fetchall()

        match_title = None
        for (stored_title,) in all_titles:
            if search_input in stored_title.lower():
                match_title = stored_title
                break

        if not match_title:
            conn.close()
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "Book was not found")
            return

        cursor.execute("SELECT word, frequency FROM word_frequencies WHERE book_title = ?", (match_title,))
        results = cursor.fetchall()
        conn.close()

        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, f"Top words for '{match_title}':\n\n")
        for word, freq in results:
            self.result_text.insert(tk.END, f"{word}: {freq}\n")

    def search_url(self):
        """Downloads a book from a URL, analyzes it, and stores its title and top words."""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Input Error", "Please enter a URL.")
            return
        try:
            text_url, title = get_text_url_and_title(url)
            response = urllib.request.urlopen(text_url)
            raw_text = response.read().decode("utf-8")
            top_words = get_top_words(raw_text)

            # Save to database
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO books (title) VALUES (?)", (title,))
            cursor.execute("DELETE FROM word_frequencies WHERE book_title = ?", (title,))
            cursor.executemany(
                "INSERT INTO word_frequencies (book_title, word, frequency) VALUES (?, ?, ?)",
                [(title, word, freq) for word, freq in top_words]
            )
            conn.commit()
            conn.close()

            # Display results
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"Book Title: {title}\n\n")
            for word, freq in top_words:
                self.result_text.insert(tk.END, f"{word}: {freq}\n")

        except Exception as e:
            messagebox.showerror("Download Error", str(e))

# Main runner
if __name__ == "__main__":
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError("This program requires the 'beautifulsoup4' package.'")

    init_db()  # Set up the database
    root = tk.Tk()  # Create main window
    app = BookSearchApp(root)  # Create app logic
    root.mainloop()  # Run the GUI loop



