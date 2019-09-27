from flask import Flask, abort


app = Flask(__name__)


def read_file(filename):
    with open(filename) as f:
        return f.read()


@app.route('/')
def base():
    return b'hello'


@app.route('/index.html')
def index():
    return read_file('index.html')


@app.route('/page1.html')
def page1():
    return read_file('page1.html')


@app.route('/page2.html')
def page2():
    return read_file('page2.html')


@app.route('/page3.html')
def page3():
    return read_file('page3.html')


@app.route('/err/<int:code>')
def return_code(code):
    abort(code)
