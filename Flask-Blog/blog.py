from flask import Flask, render_template, flash, redirect, url_for, session,logging,request, make_response
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField,PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.Length(min = 4, max =25)])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min = 5, max =35)])
    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Giriniz!")])
    password = PasswordField("Parola", validators=[
        validators.DataRequired(message = "Lütfen bir parola belirleyin!"),
        validators.EqualTo(fieldname = "confirm", message = "Parolanız Uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")
    
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key = "ybblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"


mysql = MySQL(app)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


# kullanıcı giriş decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu Sayfayı Görüntülemek için lütfen giriş yapın.", "danger")
            return redirect(url_for("login"))
    return decorated_function

# Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles"
    result = cursor.execute(sorgu)

    if result > 0: 
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles )
    else: 
        return render_template("articles.html")


# Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * FROM articles WHERE author = %s"
    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

# Kayıt Olma
@app.route("/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "INSERT INTO users (name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(sorgu,(name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarılı Bir Şekilde Kayıt Oldunuz!", "success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)
    

# Giriş Yap
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)

    if request.method == "POST":
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM users WHERE username = %s"
        result = cursor.execute(sorgu, (username,))
        
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password, real_password):
                flash("Başarıyla Giriş Yaptınız.", "success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index")) # giriş yaptıktan sonra gönderilen sayfa
            else:
                flash("Parolanızı Hatalı Girdiniz, lütfen tekrar deneyiniz.", "danger") # şifresi doğru değil ise hatalı mesaj gönderiyoruz
                return redirect(url_for("login")) # hatalı giriş yapınca gönderilen sayfa
        else:
            flash("Böyle bir kullanıcı bulunamadı.", "danger") # kullanıcı adı bulamazsa flash mesajı yolluyoruz
            return redirect(url_for("login")) # kullanıcı adı bulamazsa gönderileceği sayfa
    return render_template("login.html", form = form) # login.html sayfasından formu gönderiyoruz

#article
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

# Logout işlemi çıkış yap
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and  form.validate():
        title = form.title.data
        content = form.content.data
        
        cursor =  mysql.connection.cursor()
        sorgu = "INSERT INTO articles (title, author, content) VALUES (%s,%s,%s)"
        cursor.execute(sorgu, (title, session["username"], content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi.", "success")
        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "SELECT * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu, (session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2, (id,))
        sorgu3 = "INSERT from articles where id = %s"
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz bulunmamaktadır!", "danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>", methods =  ["GET", "POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "SELECT * FROM articles WHERE id = %s and author = %s"
        result = cursor.execute(sorgu, (id, session["username"]))
        
        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yoktur!", "danger")
            return redirect(url_for(index))
        
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form)  


    else:
        # POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu2 = "UPDATE articles SET title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2, (newTitle, newContent, id))
        mysql.connection.commit()
        flash("Makale Başarıyla Güncellendi", "success")
        return redirect(url_for("dashboard"))
        

# Makale Form
class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min=5, max=100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min=5)])

#Arama Url
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu =  "SELECT * from articles where title like '%" + keyword + "%' "
        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunmadı.", "danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)
        

# Test Cookie
@app.route("/setcookie")
def setcookie():
    resp = make_response('Setting The Cookie')
    resp.set_cookie("BRL", "Barlas Portal")
    return resp       
    
# Test upload
@app.route("/upload", methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        f = request.files['the_file']
        f.save('/var/www/uploads/uploaded_file.txt')
    else: 
        return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
