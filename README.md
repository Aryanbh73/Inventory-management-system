# 🏪 Smart Inventory Management System

A full-stack inventory management system built with Python, MySQL, Streamlit, Excel, Google Sheets, and Machine Learning.

The system helps businesses manage products, suppliers, sales, purchases, stock levels, and inventory analytics while providing AI-based demand forecasting and reorder recommendations.

---

## 🚀 Features

### 📊 Dashboard
- Total products
- Total stock
- Low-stock products
- Out-of-stock products
- Inventory value
- Sales overview
- Top-selling products

### 📦 Product Management
- Add products
- View products
- Update products
- Delete products
- Search and filter products
- Automatic stock tracking

### 🏢 Supplier Management
- Add suppliers
- View suppliers
- Update suppliers
- Delete suppliers
- Supplier-product mapping

### 💰 Sales Management
- Create sales
- Automatic stock reduction
- Sales transaction recording
- Sales history
- Low-stock detection

### 🛒 Purchase Management
- Create purchase orders
- Assign suppliers
- Add products and quantities
- Track pending orders
- Receive purchases
- Automatic stock increase
- Purchase transaction history

### 🤖 AI Inventory Intelligence
- Demand forecasting
- 7-day demand prediction
- 30-day demand prediction
- Historical vs predicted demand
- AI reorder recommendations
- Recommended purchase quantity
- MAE and RMSE model evaluation

### ⚠️ Inventory Alerts
- Low stock
- Out of stock
- Reorder required
- Healthy stock status

### 📈 Analytics
- Sales revenue
- Purchase expenses
- Product-wise sales
- Sales trends
- Purchase trends
- Inventory analysis

### 🔄 Automatic Data Synchronization
- Excel synchronization
- Google Sheets synchronization
- Automatic updates after inventory transactions
- Manual synchronization option

---

## 🛠️ Technology Stack

### Backend
- Python
- MySQL

### Frontend / Dashboard
- Streamlit

### Data Processing
- Pandas
- NumPy

### Machine Learning
- Scikit-learn
- Random Forest Regressor

### Data Export & Synchronization
- OpenPyXL
- Google Sheets API
- gspread

### Authentication
- Google Service Account

### Version Control
- Git
- GitHub

---

## 🏗️ System Architecture

```text
                    SMART INVENTORY SYSTEM
                              │
                ┌─────────────┴─────────────┐
                │                           │
             Dashboard                  MySQL
             Streamlit                 Database
                │                           │
        ┌───────┼────────┐          ┌───────┼────────┐
        │       │        │          │       │        │
      Sales  Purchase  Products  Suppliers Transactions
        │       │        │          │       │
        └───────┴────────┴──────────┴───────┘
                              │
                              ▼
                         ML Pipeline
                              │
                    ┌─────────┴─────────┐
                    │                   │
             Demand Forecasting    Reorder Engine
                    │                   │
                    └─────────┬─────────┘
                              ▼
                     AI Recommendations
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
              Excel                  Google Sheets
