from gadget_hub import create_app, mysql
from gadget_hub.models import User

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'mysql': mysql,
        'User': User
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000)

