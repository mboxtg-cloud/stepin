import streamlit as st
import pandas as pd
import json
import uuid
import re
from datetime import datetime
import google.generativeai as genai
from io import BytesIO

# ==========================================
# 0. DEEP FILE PARSING ENGINES
# ==========================================
def extract_text_from_txt(file_bytes):
    try:
        return file_bytes.decode("utf-8")
    except Exception:
        return file_bytes.decode("latin-1")

def extract_text_from_docx(file_bytes):
    import zipfile
    import xml.etree.ElementTree as ET
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            paragraphs = []
            for elem in root.iter():
                if elem.tag.endswith('t'):
                    paragraphs.append(elem.text)
            return " ".join(paragraphs)
    except Exception as e:
        return f"[Error parsing DOCX file: {str(e)}]"

def extract_text_from_pdf(file_bytes):
    try:
        content = file_bytes.decode('utf-8', errors='ignore')
        text_blocks = re.findall(r'BT(.*?)ET', content, re.DOTALL)
        extracted = []
        for block in text_blocks:
            strings = re.findall(r'\((.*?)\)', block)
            if strings:
                extracted.append(" ".join(strings))
        result = " ".join(extracted)
        if not result.strip() or len(result.strip()) < 10:
            return "[PDF structure complex. Data fallback applied.]"
        return result
    except Exception as e:
        return f"[Error parsing PDF: {str(e)}]"

# ==========================================
# 1. INITIALIZE DATABASES & CONFIGURATION
# ==========================================
st.set_page_config(page_title="Agentic GTM Workspace", layout="wide")

# API Configuration check
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    api_key_input = st.sidebar.text_input("Enter Gemini API Key:", type="password")
    if api_key_input:
        genai.configure(api_key=api_key_input)

# In-Memory Customer State Database
if "customers" not in st.session_state:
    st.session_state.customers = {
        "John Doe": {"address": "123 Main St, New York", "loyalty_points": 120},
        "Jane Smith": {"address": "456 Oak Ave, California", "loyalty_points": 45}
    }

# In-Memory Logistics Vendor Database
if "vendors" not in st.session_state:
    st.session_state.vendors = {
        "Alpha Logistics": {"location": "New York", "rating": 4.8, "tier": "Budget"},
        "Apex Delivery": {"location": "California", "rating": 4.5, "tier": "Premium"},
        "Global Express": {"location": "Global", "rating": 4.2, "tier": "Economy"}
    }

# In-Memory Active Product Catalog Default Settings
if "catalog" not in st.session_state:
    st.session_state.catalog = [
        {"id": "PROD001", "name": "Standard Widget", "price": 25.00, "inventory": 100},
        {"id": "PROD002", "name": "Premium Gadget", "price": 75.00, "inventory": 40}
    ]

if "faq" not in st.session_state:
    st.session_state.faq = "Default Policy Base: Refund valid within 14 days. Standard logistics apply."

if "cart" not in st.session_state:
    st.session_state.cart = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_customer" not in st.session_state:
    st.session_state.current_customer = None

# ==========================================
# 2. CORE AGENTIC UTILITIES & AI INTELLIGENCE
# ==========================================
def run_agentic_pipeline(user_prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        system_instruction = f"""
        You are an autonomous AI Agent managing the storefront GTM workflow for a small business.
        Available Catalog: {json.dumps(st.session_state.catalog)}
        Available Delivery Vendors: {json.dumps(st.session_state.vendors)}
        T&C and FAQ Policy Context: {st.session_state.faq}
        
        Provide helpful responses to the client. If they ask about items, prices, or policies, quote them directly.
        If they want to select or filter vendors, evaluate their intent against the Vendor parameters.
        Keep replies short, objective, and plain text.
        """
        response = model.generate_content(system_instruction + "\nUser: " + user_prompt)
        return response.text
    except Exception as e:
        return f"AI Agent Offline. Error: {str(e)}"

# ==========================================
# 3. INTERFACE FRAMEWORKS & UIs
# ==========================================
st.title("Plain Agentic GTM Unified Portal")

with st.sidebar:
    st.header("⚙️ Vendor Upload Center")
    
    # Returning Customer Identification Array
    customer_choice = st.selectbox("Select Customer Node (Simulation):", ["New Customer"] + list(st.session_state.customers.keys()))
    st.session_state.current_customer = None if customer_choice == "New Customer" else customer_choice
    
    st.markdown("---")
    
    # 1. Excel Spreadsheet Catalog Uploader
    st.subheader("1. Catalog Upload (.xlsx)")
    catalog_file = st.file_uploader("Upload catalog sheet", type=["xlsx"])
    if catalog_file is not None:
        try:
            df = pd.read_excel(catalog_file)
            df.columns = df.columns.str.lower()
            st.session_state.catalog = df.to_dict(orient="records")
            st.success("✅ Catalog overwritten with Excel data!")
        except Exception as err:
            st.error(f"Excel error: {err}")
            
    st.markdown("---")
    
    # 2. Document Policy & FAQ Uploader
    st.subheader("2. Policies & FAQs Upload")
    doc_file = st.file_uploader("Upload text, docx, or pdf", type=["txt", "docx", "pdf"])
    if doc_file is not None:
        file_bytes = doc_file.read()
        file_ext = doc_file.name.split(".")[-1].lower()
        parsed_text = ""
        
        with st.spinner("Analyzing document layers..."):
            if file_ext == "txt":
                parsed_text = extract_text_from_txt(file_bytes)
            elif file_ext == "docx":
                parsed_text = extract_text_from_docx(file_bytes)
            elif file_ext == "pdf":
                parsed_text = extract_text_from_pdf(file_bytes)
                
        if parsed_text:
            st.session_state.faq = parsed_text
            st.success(f"✅ Ingested context successfully.")

# Multi-Tab Functional Application Workspace
tab1, tab2, tab3 = st.tabs(["💬 Agent Customer Chat", "📦 Inventory & Pricing Matrix", "🧾 Order, Invoicing & Ledger Pipeline"])

# ---- TAB 1: CUSTOMER CONVERSATION & AGENT ROUTER ----
with tab1:
    st.header("Autonomous AI Shopping Agent Desk")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
    if user_input := st.chat_input("Ask questions or query logistics routes:"):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        agent_reply = run_agentic_pipeline(user_input)
        st.session_state.chat_history.append({"role": "assistant", "content": agent_reply})
        with st.chat_message("assistant"):
            st.write(agent_reply)

# ---- TAB 2: CATALOG MATRIX MANAGEMENT ----
with tab2:
    st.header("Real-Time Inventory Ledger")
    st.table(pd.DataFrame(st.session_state.catalog))
    
    st.header("Interactive Order Desk")
    if st.session_state.catalog:
        selected_prod = st.selectbox("Select Product to add to current contract:", [p.get("name", "Unknown") for p in st.session_state.catalog])
        prod_details = next((item for item in st.session_state.catalog if item.get("name") == selected_prod), None)
        
        if prod_details and st.button(f"Add 1x {selected_prod} to Basket"):
            st.session_state.cart.append(prod_details)
            st.toast("Item staged.")
    else:
        st.warning("No catalog loaded. Please upload an Excel array via the sidebar panel.")


# ---- TAB 3: TRANSACTION PIPELINE ----
with tab3:
    st.header("Active Transaction Terminal")
    if not st.session_state.cart:
        st.info("The transaction basket is empty.")
    else:
        subtotal = sum(float(item.get("price", 0)) for item in st.session_state.cart)
        buyer_name = st.session_state.current_customer if st.session_state.current_customer else "Walk-in Guest Account"
        
        st.subheader("1. Route Fulfillment Options")
        vendor_choice = st.selectbox("Assign Logistics Vendor:", list(st.session_state.vendors.keys()))
        selected_v_info = st.session_state.vendors[vendor_choice]
        
        v_rating = st.slider("Rate vendor execution:", 1.0, 5.0, 5.0, 0.5)
        if st.button("Log Score"):
            st.session_state.vendors[vendor_choice]["rating"] = round((selected_v_info['rating'] + v_rating) / 2, 2)
            st.success("Performance metric adjusted.")

        # =========================================================================
        # YOUR SNIPPET LIVES EXACTLY HERE (INSIDE THE 'ELSE' BLOCK OF TAB 3)
        # =========================================================================
        st.subheader("2. Finalized Invoice Statement")
        invoice_id = str(uuid.uuid4())[:8].upper()
        invoice_text = f"""
        INVOICE IDENTIFIER: #{invoice_id}
        TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        CLIENT ACCOUNT: {buyer_name}
        ASSIGNED TRANSPORTER: {vendor_choice}
        GROSS BALANCE DUE: ${subtotal:.2f}
        """
        st.code(invoice_text, language="text")
        
        if st.button("Authorize Credit Transaction & Process Ledger"):
            # Update internal quantities
            for item in st.session_state.cart:
                for db_item in st.session_state.catalog:
                    if db_item.get("id") == item.get("id") and db_item.get("inventory", 0) > 0:
                        db_item["inventory"] -= 1
            
            if st.session_state.current_customer:
                st.session_state.customers[st.session_state.current_customer]["loyalty_points"] += int(subtotal // 10)
                
            st.success("💳 Transaction Approved! Inventory updated.")
            st.subheader("3. Payment Receipt Status")
            st.code(f"PAID RECEIPT REC-{uuid.uuid4().hex[:6].upper()}\nRECEIVED AMOUNT: ${subtotal:.2f}\nCleared via {vendor_choice}.", language="text")
            st.session_state.cart = []
