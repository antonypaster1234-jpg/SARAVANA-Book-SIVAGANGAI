from flask import Flask,render_template,request,redirect,url_for,session,flash,abort
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3,os,uuid
app=Flask(__name__); app.secret_key="change-this-secret-key"
ROOT=os.path.dirname(os.path.abspath(__file__)); UP=os.path.join(ROOT,"static","uploads"); DB=os.path.join(ROOT,"shop.db")
os.makedirs(UP,exist_ok=True)
OWNER_USER="owner"; OWNER_PASS="saravana123"
def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.execute("""CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT,description TEXT,mrp REAL,offer REAL,image TEXT,category TEXT)""")
  c.execute("""CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY,product_id INTEGER,name TEXT,rating INTEGER,comment TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)""")
  c.execute("""CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,name TEXT,phone TEXT,address TEXT,total REAL,items TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)""")
init()
def owner(f):
 @wraps(f)
 def w(*a,**k):
  if not session.get("owner"): return redirect(url_for("login"))
  return f(*a,**k)
 return w
@app.context_processor
def shared(): return {"cart_count":sum(session.get("cart",{}).values()),"is_owner":session.get("owner",False)}
@app.route("/")
def home():
 q=request.args.get("q","").strip(); cat=request.args.get("category","")
 sql="SELECT * FROM products WHERE (name LIKE ? OR description LIKE ? OR category LIKE ?)"; term="%"+q+"%"
 args=[term,term,term]
 if cat: sql+=" AND category=?"; args.append(cat)
 with conn() as c:
  products=c.execute(sql+" ORDER BY id DESC",args).fetchall()
  cats=[x[0] for x in c.execute("SELECT DISTINCT category FROM products WHERE category!=''")]
  ratings={p["id"]:c.execute("SELECT AVG(rating),COUNT(*) FROM reviews WHERE product_id=?",(p["id"],)).fetchone() for p in products}
 return render_template("home.html",products=products,q=q,cats=cats,cat=cat,ratings=ratings)
@app.route("/product/<int:pid>",methods=["GET","POST"])
def detail(pid):
 with conn() as c:
  p=c.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
  if not p: abort(404)
  if request.method=="POST":
   n=request.form.get("name","").strip(); cm=request.form.get("comment","").strip()
   try: r=int(request.form.get("rating",5))
   except: r=0
   if n and cm and 1<=r<=5:
    c.execute("INSERT INTO reviews(product_id,name,rating,comment) VALUES(?,?,?,?)",(pid,n,r,cm)); flash("Thanks for your review!")
    return redirect(url_for("detail",pid=pid))
   flash("Please complete all review fields.")
  reviews=c.execute("SELECT * FROM reviews WHERE product_id=? ORDER BY id DESC",(pid,)).fetchall()
  avg=c.execute("SELECT AVG(rating),COUNT(*) FROM reviews WHERE product_id=?",(pid,)).fetchone()
 return render_template("detail.html",p=p,reviews=reviews,avg=avg)
@app.route("/cart/add/<int:pid>",methods=["POST"])
def add(pid):
 with conn() as c:
  if not c.execute("SELECT id FROM products WHERE id=?",(pid,)).fetchone(): abort(404)
 cart=session.get("cart",{}); cart[str(pid)]=cart.get(str(pid),0)+1; session["cart"]=cart
 flash("Added to cart!"); return redirect(request.referrer or url_for("home"))
@app.route("/buy/<int:pid>",methods=["POST"])
def buy(pid):
 session["cart"]={str(pid):1}; return redirect(url_for("cart"))
@app.route("/cart")
def cart():
 items=[]; total=0
 with conn() as c:
  for pid,qty in session.get("cart",{}).items():
   p=c.execute("SELECT * FROM products WHERE id=?",(int(pid),)).fetchone()
   if p: items.append((p,qty,p["offer"]*qty)); total+=p["offer"]*qty
 return render_template("cart.html",items=items,total=total)
@app.route("/cart/update/<int:pid>",methods=["POST"])
def update(pid):
 cart=session.get("cart",{})
 try: qty=int(request.form.get("qty",1))
 except: qty=1
 if qty<1: cart.pop(str(pid),None)
 else: cart[str(pid)]=min(qty,99)
 session["cart"]=cart; return redirect(url_for("cart"))
@app.route("/checkout",methods=["GET","POST"])
def checkout():
 items=[]; total=0
 with conn() as c:
  for pid,qty in session.get("cart",{}).items():
   p=c.execute("SELECT * FROM products WHERE id=?",(int(pid),)).fetchone()
   if p: items.append((p,qty,p["offer"]*qty)); total+=p["offer"]*qty
 if not items: return redirect(url_for("home"))
 if request.method=="POST":
  n=request.form.get("name","").strip(); ph=request.form.get("phone","").strip(); addr=request.form.get("address","").strip()
  if n and ph and addr:
   items_str=", ".join([f"{p['name']} (x{qty} - ₹{round(sub,2)})" for p,qty,sub in items])
   with conn() as c:
    c.execute("INSERT INTO orders(name,phone,address,total,items) VALUES(?,?,?,?,?)",(n,ph,addr,total,items_str))
   session["cart"]={}; return render_template("success.html",name=n,total=total)
  flash("Please fill all delivery details.")
 return render_template("checkout.html",items=items,total=total)
@app.route("/owner/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  if request.form.get("username")==OWNER_USER and request.form.get("password")==OWNER_PASS:
   session["owner"]=True; return redirect(url_for("dashboard"))
  flash("Wrong owner login.")
 return render_template("login.html")
@app.route("/owner/logout")
def logout(): session.pop("owner",None); return redirect(url_for("home"))
@app.route("/owner")
@owner
def dashboard():
 with conn() as c:
  products=c.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
  count=c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
  order_count=c.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
 return render_template("owner.html",products=products,count=count,order_count=order_count)
@app.route("/owner/add",methods=["GET","POST"])
@owner
def add_product():
 if request.method=="POST":
  try: mrp=float(request.form["mrp"]); offer=float(request.form["offer"])
  except: flash("Enter valid prices."); return redirect(url_for("add_product"))
  name=request.form.get("name","").strip()
  if not name or mrp<=0 or offer<0 or offer>mrp: flash("Check product name and prices."); return redirect(url_for("add_product"))
  image=request.files.get("image"); filename=""
  if image and image.filename:
   ext=image.filename.rsplit(".",1)[-1].lower()
   if ext not in ["jpg","jpeg","png","webp"]: flash("Use JPG, PNG or WEBP image."); return redirect(url_for("add_product"))
   filename=uuid.uuid4().hex+"."+ext; image.save(os.path.join(UP,secure_filename(filename)))
  with conn() as c: c.execute("INSERT INTO products(name,description,mrp,offer,image,category) VALUES(?,?,?,?,?,?)",(name,request.form.get("description",""),mrp,offer,filename,request.form.get("category","General")))
  flash("Product added!"); return redirect(url_for("dashboard"))
 return render_template("add.html")
@app.route("/owner/delete/<int:pid>",methods=["POST"])
@owner
def delete(pid):
 with conn() as c:
  c.execute("DELETE FROM reviews WHERE product_id=?",(pid,)); c.execute("DELETE FROM products WHERE id=?",(pid,))
 return redirect(url_for("dashboard"))
@app.route("/owner/reviews")
@owner
def owner_reviews():
 with conn() as c: reviews=c.execute("SELECT reviews.*,products.name product FROM reviews JOIN products ON products.id=reviews.product_id ORDER BY reviews.id DESC").fetchall()
 return render_template("owner_reviews.html",reviews=reviews)
@app.route("/owner/orders")
@owner
def owner_orders():
 with conn() as c: orders=c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
 return render_template("owner_orders.html",orders=orders)
if __name__=="__main__": init(); app.run(debug=True)
