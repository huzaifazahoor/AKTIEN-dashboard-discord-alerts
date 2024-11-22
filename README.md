Django Boilerplate
==================

A starter template for Django projects, including essential configurations, a basic project structure, and CI/CD pipeline setup for deployment on Google App Engine using GitHub Actions.

Features
--------

-   Django 5.0.7
-   Environment variable management with `python-dotenv`
-   Separate settings for development and production environments
-   Database configuration for both SQLite (development) and PostgreSQL (production)
-   Simple CI/CD pipeline configuration with GitHub Actions
-   Deployment-ready for Google App Engine
-   Added the cloud sql proxy as well.

Setup
-----

### Prerequisites

-   Python 3.x
-   pip
-   Virtualenv (recommended)

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/huzaifazahoor/django-boilerplate.git
    cd django-boilerplate
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate
    ```

3.  **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file in the project root and add your environment variables:**

    ```env
    DJANGO_SECRET_KEY=your_secret_key
    SERVER=development  # Change to 'production' in production environment
    ```

    **Note:** Add other variables if you are using pgSQL or MySQL. 

5.  **Run database migrations:**

    ```bash
    python manage.py makemigrations
    python manage.py migrate```

6.  **Create a superuser for the admin interface:**

    `bash
    python manage.py createsuperuser```

7.  **Run the development server:**

    ```bash
    python manage.py runserver
    ```

    Visit `http://127.0.0.1:8000/` to see the application in action.

Project Structure
-----------------

```markdown
project_core/
├── manage.py
├── project_core/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── requirements.txt
├── .env
├── .gitignore
├── app.yaml
├── README.md
├── cloud_sql_proxy.exe
```

Deployment
----------

This project includes a `deploy.yml` file configured for GitHub Actions. Before deploying, update the `deploy.yml` file and change the branch name from `dummy-branch` to your desired branch.

To deploy on Google App Engine, ensure you have the Google Cloud SDK installed and authenticated.

Contributing
------------

Contributions are welcome! Please fork the repository and create a pull request.

License
-------

This project is licensed under the MIT License.

* * * * *

**Note:** The project is currently under development. Some features and configurations might change in the future.