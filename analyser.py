# ✅ Must be the first Streamlit command
import streamlit as st
st.set_page_config(page_title="UPI Analyzer", layout="wide")

# 🔧 Imports
import pandas as pd
import fitz  # PyMuPDF
import re
from datetime import datetime
import openai

# --------------- Text Extraction from PDF --------------- #
def extract_text_lines(uploaded_file):
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
    return text.split("\n")

# --------------- Group Lines into Transaction Blocks --------------- #
def group_transaction_blocks(lines):
    blocks = []
    current_block = []
    for line in lines:
        if re.match(r"\d{2} \w{3} \d{2}", line):
            if current_block:
                blocks.append(" ".join(current_block))
                current_block = []
        current_block.append(line.strip())
    if current_block:
        blocks.append(" ".join(current_block))
    return blocks

# --------------- Parse Transactions from Blocks --------------- #
def parse_transaction_blocks(blocks):
    transactions = []
    for block in blocks:
        date_match = re.search(r"(\d{2} \w{3} \d{2})", block)
        amount_match = re.search(r"(\d{1,3}(?:,\d{3})*(?:\.\d{2}))", block)
        if date_match and amount_match:
            try:
                date = datetime.strptime(date_match.group(1), "%d %b %y").strftime("%Y-%m-%d")
                amount = float(amount_match.group(1).replace(",", ""))
                desc = re.sub(r"\d{2} \w{3} \d{2}", "", block).strip()
                tx_type = "Credit" if "RETURN" in block.upper() or "INTEREST" in block.upper() else "Debit"
                transactions.append({
                    "date": date,
                    "description": desc,
                    "amount": amount,
                    "type": tx_type
                })
            except:
                continue
    return transactions

# --------------- Categorize Transactions --------------- #
def categorize_transaction(description):
    desc = description.lower()
    if "zomato" in desc or "swiggy" in desc:
        return "Food"
    elif "googlepay" in desc or "paytm" in desc or "upi" in desc:
        return "UPI Payment"
    elif "imps" in desc or "transfer" in desc:
        return "Bank Transfer"
    elif "interest" in desc or "salary" in desc:
        return "Income"
    elif "recharge" in desc or "bill" in desc:
        return "Utilities"
    else:
        return "Others"

# --------------- Get Financial Insights from LLM --------------- #
def get_llm_insight(transactions_summary):
    openai.api_key = st.secrets["OPENAI_API_KEY"]  # Set this in Hugging Face Secrets

    prompt = f"""
    Analyze the user's UPI transaction summary:
    {transactions_summary}

    Give:
    - Monthly savings percentage
    - Wasteful spending categories
    - 3 personalized financial advice points
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ LLM failed: {e}"

# --------------- Streamlit UI --------------- #
st.title("📄 UPI Statement Analyzer with AI Advice")

uploaded_file = st.file_uploader("📂 Upload your UPI statement PDF", type=["pdf"])

if not uploaded_file:
    st.warning("Please upload a UPI statement PDF to begin.")
    st.stop()

# --- Extract & Parse ---
lines = extract_text_lines(uploaded_file)
blocks = group_transaction_blocks(lines)
txns = parse_transaction_blocks(blocks)

# Check if data was parsed
if not txns:
    st.error("⚠️ No valid transactions found. Please check your PDF format.")
    st.stop()

# Categorize
for txn in txns:
    txn["category"] = categorize_transaction(txn["description"])

df = pd.DataFrame(txns)

if "date" not in df.columns or df.empty:
    st.error("⚠️ Error processing transactions. 'date' column missing.")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# --- Display Table ---
st.success("✅ Transactions parsed successfully!")
st.subheader("📄 Parsed Transactions")
st.dataframe(df)

# --- Summary Metrics ---
st.subheader("📊 Summary Metrics")
total_income = df[df["type"] == "Credit"]["amount"].sum()
total_expense = df[df["type"] == "Debit"]["amount"].sum()
savings = total_income - total_expense
savings_percent = (savings / total_income) * 100 if total_income > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Income", f"₹{total_income:,.2f}")
col2.metric("Total Expenses", f"₹{total_expense:,.2f}")
col3.metric("Savings %", f"{savings_percent:.2f}%")

# --- Category Chart ---
st.subheader("📂 Category-wise Expenses")
category_expenses = df[df["type"] == "Debit"].groupby("category")["amount"].sum()
st.bar_chart(category_expenses)

# --- LLM Insights ---
st.subheader("🤖 AI-Powered Financial Advice")
summary_dict = df.groupby("category")["amount"].sum().to_dict()
insight = get_llm_insight(summary_dict)
st.markdown(insight)

# --- CSV Download ---
st.download_button("📥 Download CSV", df.to_csv(index=False), file_name="transactions.csv", mime="text/csv")
