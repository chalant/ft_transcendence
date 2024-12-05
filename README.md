# FT_TRANSCENDENCE
A single-page application website for real-time multiplayer arcade games.
Written in JavaScript and Python, using the Django framework with a microservices architecture.
Using PostgreSQL to store user data and game history.
Using Docker to build the server.

## User Management
- Users can subscribe and log into the website in a secure way.
- Users can update their information, including an avatar.
- Users can add others as friends and view their online status.
- User profiles display stats, such as wins and losses.
- Each user has a Match History including 1v1 games, dates, and relevant details, accessible to logged-in users.
- remote authentication is integrated with OAuth and available to '42' members.

![Screenshot (71)](https://github.com/user-attachments/assets/ec9e10e4-c632-4ffe-8b9f-a8597e79c254)
![Screenshot (74)](https://github.com/user-attachments/assets/c7863c71-2820-459a-8ff0-30d1953ea647)

## Games
Games can be played locally on one computer or remotely between users.
You can play a quick match or join a tournament.
Both games run server-side.

#### Pong:
Choice between a classic 2D scheme or 3D visuals.
![Screenshot (72)](https://github.com/user-attachments/assets/9ffb5593-ea98-46e3-8a4b-a7d54f7efd80)
![Screenshot (82)](https://github.com/user-attachments/assets/3201ff5d-f5ec-4fd5-ae55-7c42e580c984)

#### Snake:
![Screenshot (79)](https://github.com/user-attachments/assets/72d85f36-423b-4d66-8a19-cf4a88ebc5a5)

##### Tournament setup:
![Screenshot (68)](https://github.com/user-attachments/assets/47d370e6-001d-483d-8888-9d33cc5e8364)
