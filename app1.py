from flask import Flask, render_template

app = Flask(__name__)

# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')

# Route for another page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')


@app.route('/start')
def start():
    return render_template('start.html')

@app.route('/powerpoint')
def powerpoint():
    return render_template('powerpoint.html')

@app.route('/Gtype1')
def Gtype1():
    return render_template('Gtype1.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            file_path = os.path.join(folderpath, file.filename)
            file.save(file_path)
            load_images()  # Reload images after upload
            flash('File uploaded successfully')
            return redirect(url_for('upload'))
    return render_template('upload.html')



if __name__ == '__main__':
    app.run(debug=True)