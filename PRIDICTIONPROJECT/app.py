from flask import Flask, render_template, request, make_response,redirect,url_for,session
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import jinja2
from pymongo import MongoClient #driver
from werkzeug.security import generate_password_hash, check_password_hash
import hashlib


app = Flask(__name__)
app.secret_key = "reg"  # Replace with a secret key
client = MongoClient("mongodb://localhost:27017")  # MongoDB server
db = client["pro"]  #database name
users = db["user"] #collection
contacts =db["contact"]




# Load and preprocess the dataset
df = pd.read_csv('DATASET.csv')
encoder = LabelEncoder()
df['Category'] = encoder.fit_transform(df['Category'])


@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        return render_template('main2.html', username=username)
    else:
        return render_template('main2.html', username=None)

#registed

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None  # Initialize the error message variable

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        phonenumber=request.form.get("phone-number")
        email=request.form.get("email")

        hashed_password = generate_password_hash(password) #password incripted

        # Check if the username already exists in the database
        if users.find_one({"username": username}):
            error = "Username already exists, please choose another one."

        # If the username doesn't exist, proceed with registration
        else:
            print(f"Registering user: {username}")
            users.insert_one({"username": username, "password": hashed_password, "phonenumber":phonenumber, "email":email})
            print(f"User {username} registered successfully")
            return redirect(url_for('login'))

    # Pass the error message to the template
    return render_template("register.html", error_message=error)



#contact
@app.route("/contact", methods=["GET","POST"])
def contact():
    error=None

    if request.method =="POST":
        name=request.form.get("name")
        email=request.form.get("email")
        message=request.form.get("message")

        print(f"sending contact:{name}")
        contacts.insert_one({"name":name, "email":email,"message":message})
        print(f"Send succesffully")
        return redirect(url_for('home'))
    
    return render_template("contact.html", error_message=error)



#login
@app.route("/", methods=["GET", "POST"])
def login():
    error = None 
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = users.find_one({"username": username})

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("home"))  # Redirect to the index endpoint

        error = "Invalid username or password."


    return render_template("login.html",error=error)



@app.route('/index', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_category = request.form['category']
        user_marks = float(request.form['marks'])

        user_category_encoded = encoder.transform([user_category])[0]

        filtered_data = df[(df['Category'] == user_category_encoded) & (df['Marks'] >= user_marks)]

        user_input = pd.DataFrame([[user_category_encoded, user_marks]], columns=['Category', 'Marks'])
        data_for_similarity = pd.concat([user_input] * len(filtered_data), ignore_index=True)
        similarity_matrix = cosine_similarity(data_for_similarity, filtered_data[['Category', 'Marks']].values)

        N = 10
        top_n_indices = similarity_matrix[0].argsort()[-N:][::-1]

        recommended_colleges = list(filtered_data.iloc[top_n_indices]['College'])  # Convert to list
        return render_template('index.html', recommended_colleges=recommended_colleges)

    return render_template('index.html', recommended_colleges=[])

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    colleges = request.form.get('college_list').split(', ')

    response = make_response(generate_pdf_bytes(colleges))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=recommended_colleges.pdf'
    return response

def generate_pdf_bytes(colleges):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    p.drawString(100, 750, 'Recommended Colleges:')
    y_position = 730

    for college in colleges:
        p.drawString(150, y_position, college)
        y_position -= 20

    p.save()
    buffer.seek(0)
    return buffer.read()

if __name__ == '__main__':
    app.run(debug=True)