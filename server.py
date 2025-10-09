"""
Serveur web minimal pour garder le service Render actif
Ce serveur ne fait rien, il reste juste en vie
"""

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <body style="font-family: Arial; padding: 40px;">
            <h1>🤖 _Head.Soeurise - Module 1</h1>
            <p>Le service est actif.</p>
            <p>Réveil automatique programmé à 11h (heure France) chaque jour.</p>
            <p style="color: green;">✓ Service opérationnel</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {'status': 'ok', 'service': 'head-soeurise-module1'}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
