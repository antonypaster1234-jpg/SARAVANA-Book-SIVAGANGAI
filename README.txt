SARAVANA STORE - SIVAGANGAI
Features: Owner login/dashboard, public shop, search, product images, MRP and offer prices,
discount calculation, product descriptions, Add to Cart, Buy Now, demo checkout, customer reviews.

RUN ON WINDOWS / VS CODE:
1. Extract ZIP and open folder in VS Code.
2. Terminal:
   py -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   py app.py
3. Open http://127.0.0.1:5000

OWNER LOGIN:
Username: owner
Password: saravana123

IMPORTANT:
Change OWNER_USER, OWNER_PASS and app.secret_key in app.py before deployment.
Checkout is a demonstration only: no real orders, payments, SMS, or delivery are processed.
Before public launch add secure password hashing, CSRF protection, HTTPS, payment gateway,
order storage and production hosting. Turn debug off in production.
