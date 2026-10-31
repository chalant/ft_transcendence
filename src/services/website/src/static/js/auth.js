import { navigateTo } from './router.js';

export function getCookie(name) {
	var cookieValue = null;
	if (document.cookie && document.cookie != '') {
		var cookies = document.cookie.split(';');
		for (var i = 0; i < cookies.length; i++) {
			var cookie = cookies[i].trim();
			if (cookie.substring(0, name.length + 1) == (name + '=')) {
				cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
				break;
			}
		}
	}
	return cookieValue;
}

function successAlertPlaceholder(message) {
	var alertPlaceholder = document.getElementById('alert-placeholder');
	alertPlaceholder.innerHTML = `
		<div class="success-banner" id="success-alert" role="alert">
		   ${escapeHtml(message)}
		</div>
	`;

	setTimeout(() => {
		var successAlert = document.getElementById('success-alert');
		if (!successAlert)
			return;
		successAlert.classList.add('fade-out');
		successAlert.addEventListener('transitionend', () => {
			successAlert.remove();
		});
	}, 3500);
}

function updateAlertPlaceholderError(message) {
	var alertPlaceholder = document.getElementById('alert-placeholder');
	alertPlaceholder.innerHTML = `
		<div class="error-banner" role="alert">
			${escapeHtml(message)}
		</div>
	`;
}

function replaceLoginButtons(user) {
	var profileMenu = document.getElementById('profile-menu');
	profileMenu.innerHTML = `
		<div class="dropdown">
			<a class="nav-link dropdown-toggle d-flex align-items-center" href="#" id="profileDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
				<span class="ms-2 me-2 text-white">${escapeHtml(user.username)}</span>
				<div class="profile-picture-container">
					<img src="${escapeHtml(user.profile_picture)}" class="profile-picture">
				</div>
			</a>
			<ul class="dropdown-menu dropdown-menu-end" aria-labelledby="profileDropdown">
				<li><a href="/user/${escapeHtml(user.username)}" class="dropdown-item btn btn-outline-light" data-link>Profile</a></li>
				<li><a href="/settings" class="dropdown-item btn btn-outline-light" data-link>Settings</a></li>
				<li><hr class="dropdown-divider"></li>
				<li><a class="dropdown-item btn btn-outline-light" id="logout">Logout</a></li>
			</ul>
		</div>
	`;
}

function resetLoginButtons() {
	var profileMenu = document.getElementById('profile-menu');
	profileMenu.innerHTML = `
		<ul class="navbar-nav ms-auto mb-2 mb-lg-0">
			<li class="nav-item">
				<button class="btn btn-outline-light me-2" data-bs-toggle="modal" data-bs-target="#loginModal">Log in</button>
			</li>
			<li class="nav-item">
				<button class="btn btn-outline-light" data-bs-toggle="modal" data-bs-target="#signUpModal">Sign up</button>
			</li>
		</ul>
	`;
}

document.addEventListener("DOMContentLoaded", function() {
	var socket = null;

	if (window.location.pathname.startsWith("/auth/auth42/")) {
		const status = document.getElementById('status');
		if (status.innerHTML === "0") {
			const message = document.getElementById('message');
			updateAlertPlaceholderError(message.textContent);
		} else {
			successAlertPlaceholder('Welcome!');
		}
		navigateTo('/');
	}

	fetch('/auth/is_authenticated/', {
		method: 'GET',
		headers: {
			'X-CSRFToken': getCookie('csrftoken'),
			'Authorization': 'Bearer ' + localStorage.getItem('auth_token')
		},
		credentials: 'include'
	})
	.then(response => response.json())
	.then(data => {
		if (data.status === 1) {
			localStorage.setItem('auth_token', data.token);
			replaceLoginButtons(data.user);
			socket = new WebSocket('wss://' + window.location.host + '/users/status/');
		}
	});

	var loginForm = document.getElementById("login-form");
	var loginUserName = document.getElementById("login-username");
	var loginPassword = document.getElementById("login-password");


	loginForm.addEventListener('submit', function(event) {
		event.preventDefault();

		const creds = {
			username: loginUserName.value,
			password: loginPassword.value
		};

		loginForm.reset();
		fetch('/auth/login/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': getCookie('csrftoken'),
				'Authorization': 'Bearer ' + localStorage.getItem('auth_token')
			},
			body: JSON.stringify(creds),
			credentials: 'include'
		})
		.then(response => response.json())
		.then(data => {
			if (data.status === 0) {
				updateAlertPlaceholderError(data.message);
			} else {
				successAlertPlaceholder('Welcome!');
				replaceLoginButtons(data.user);
				localStorage.setItem('auth_token', data.token);
				navigateTo('/');
				if (socket != null) {
					socket.close();
				}
				socket = new WebSocket('wss://' + window.location.host + '/users/status/');
			}
			const loginModalElement = document.getElementById('loginModal');
			const loginModal = bootstrap.Modal.getInstance(loginModalElement);
			if (loginModal) {
				loginModal.hide();
			}
		});
	});

	var signupForm = document.getElementById("signup-form");
	var signupUserName = document.getElementById("signup-username");
	var signupPassword = document.getElementById("signup-password");
	var signupConfirmPassword = document.getElementById("signup-confirm-password");

	signupForm.addEventListener('submit', function(event) {
		event.preventDefault();

		const credentials = {
			'username': signupUserName.value,
			'password': signupPassword.value,
			'confirm_password': signupConfirmPassword.value
		};

		signupForm.reset();
		fetch('/auth/signup/', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-CSRFToken': getCookie('csrftoken')
			},
			body: JSON.stringify(credentials)
		})
		.then(response => response.json())
		.then(data => {
			if (data.status === 0) {
				updateAlertPlaceholderError(data.message);
			} else {
				successAlertPlaceholder('Account successfully created! Welcome!');
				replaceLoginButtons(data.user);
				localStorage.setItem('auth_token', data.token);
				navigateTo('/');
				if (socket != null) {
					socket.close();
				}
				socket = new WebSocket('wss://' + window.location.host + '/users/status/');
			}
			const signUpModalElement = document.getElementById('signUpModal');
			const signUpModal = bootstrap.Modal.getInstance(signUpModalElement);
			if (signUpModal) {
				signUpModal.hide();
			}
		});
	});

	document.addEventListener("click", function(event) {
		if (event.target.matches("#logout")) {
			event.preventDefault();
			fetch('/auth/logout/', {
				method: 'POST',
				headers: {
					'X-CSRFToken': getCookie('csrftoken'),
					'Authorization': 'Bearer ' + localStorage.getItem('auth_token')
				},
				credentials: 'include'
			})
			.then(response => response.json())
			.then(data => {
				const logoutEvent = new CustomEvent("logout", { detail: { message: "User logged out" } });
				document.dispatchEvent(logoutEvent);
				successAlertPlaceholder('You have been logged out! Bye bye!');
				resetLoginButtons();
				navigateTo('/');
			});
		}
	});
});
