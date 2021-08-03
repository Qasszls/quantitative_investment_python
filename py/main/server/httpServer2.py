from flask import Flask, request, send_from_directory

app = Flask(__name__)


@app.route('/helloQuant', methods=['GET'])
def home():
    # 设置内容
    f = open('./helloQuant/index.html', 'r', encoding='utf-8')
    response = f.read()
    f.close()
    return response


@app.route('/helloQuant/css/<file_name>', methods=['GET'])
def get_css_file(file_name):
    return send_from_directory(
        'css', './helloQuant/css/{name}'.format(name=file_name))


@app.route('/helloQuant/js/<file_name>', methods=['GET'])
def get_js_file(file_name):
    return send_from_directory('js',
                               './helloQuant/js/{name}'.format(name=file_name))


@app.route('/helloQuant/img/icons/<file_name>', methods=['GET'])
def get_img_icons_file(file_name):
    f = open('./helloQuant/img/icons/{name}'.format(name=file_name), 'rb')
    return f.read()


@app.route('/helloQuant/helloQuant/<file_name>', methods=['GET'])
def get_helloQuant_file(file_name):
    f = open('./helloQuant/helloQuant/{name}'.format(name=file_name),
             'r',
             encoding='utf-8')
    return f.read()


@app.route('/helloQuant/<file_name>', methods=['GET'])
def get_file(file_name):
    # 读取文件
    f = open('./helloQuant/{name}'.format(name=file_name),
             'r',
             encoding='utf-8')
    return f.read()


if __name__ == '__main__':
    app.run()
