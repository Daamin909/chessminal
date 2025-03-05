from flask import Flask, request, jsonify
from flask_cors import CORS

from engine import getEngineAnalysis
app = Flask(__name__)
CORS(app)

@app.route('/api/engine', methods=['POST'])
def getEngine():
    FENs = request.get_json()['fens']
    analysis = getEngineAnalysis(FENs)
    return jsonify(analysis)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port="5001", debug=True)