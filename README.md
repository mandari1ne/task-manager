# Task Manager
This project is a web application for adaptive workload and schedule management in an IT company.
The system automates task planning, employee schedule tracking, deadline monitoring, and notification delivery. 
It helps distribute workload more evenly, reduces the amount of manual work for managers, and lowers the risk of missed deadlines.

### The application provides:
- task management (creation, editing, assignment);
- a visual calendar powered by FullCalendar;
- tracking of work schedules, vacations, and personal time;
- automatic email reminders about upcoming deadlines;
- a system of task statuses, tags, departments, and users;
- centralized data storage;
- a clean and user-friendly web interface.

### Technology stack
#### Backend:
- Python/Django - business logic and server-side components;
- Celery - background task execution;
- Redis - message broker for Celery;
- PostgreSQL - primary database;
- SMTP server (MailDev) - email notifications;
- Django ORM.
#### Frontend:
- HTML, CSS;
- JavaScript;
- FullCalendar.js.
#### Infrastructure:
- Docker + Docker Compose - containerization and deployment.

### Running the Project with Docker
Make sure you have Docker and Docker Compose installed.
1. Clone the repository:
   ```
   git clone https://github.com/mandari1ne/task-manager.git
   cd project
2. Create a **.env** file and fill it with required settings:
   ```
   POSTGRES_DB=...
   POSTGRES_USER=...
   POSTGRES_PASSWORD=...
   DEFAULT_FROM_EMAIL=...
   EMAIL_HOST=...
   EMAIL_PORT=...
3. Build and start the containers:
   ```
   docker compose up --build
4. After startup, the services will be available at:
   - Django: http://localhost:8000/
   - MailDev: http://localhost:1080/
   - PostgreSQL: port 5432
   - Redis: port 6379
5. To stop the containers:
   ```
   docker compose down
