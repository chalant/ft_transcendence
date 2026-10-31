document.addEventListener("DOMContentLoaded", () => {
	document.addEventListener("submit", async (event) => {
		if (event.target.matches("#profile-picture-form")) {
			event.preventDefault();
			const formData = new FormData(event.target);

			try {
				const response = await fetch('/media/change_profile_picture/', {
					method: 'POST',
					headers: {
						'X-CSRFToken': getCookie('csrftoken'),
						"Authorization": "Bearer " + localStorage.getItem("auth_token")
					},
					body: formData,
					credentials: 'include'
				});

				const result = await response.json();
				if (result.status === 1) {
					successAlertPlaceholder(result.message);
					document.querySelector("#profile-picture-form img").src = result.new_profile_picture_url;
					document.querySelector("#profileDropdown img").src = result.new_profile_picture_url;
				} else {
					updateAlertPlaceholderError(result.message);
				}
			} catch (error) {
				console.error('Error:', error);
			}
		}

		if (event.target.matches("#username-change-form")) {
			event.preventDefault();
			const newUsername = document.getElementById("new-username").value;

			try {
				const response = await fetch('/auth/change_username/', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': getCookie('csrftoken'),
						"Authorization": "Bearer " + localStorage.getItem("auth_token")
					},
					body: JSON.stringify({ username: newUsername }),
					credentials: 'include'
				});

				const result = await response.json();
				if (result.status === 1) {
					successAlertPlaceholder(result.message);
					document.querySelector("#profileDropdown span").textContent = newUsername;
					const profileLink = document.querySelector("a[href^='/user/']");
					if (profileLink) {
						profileLink.href = `/user/${newUsername}`;
					}

				} else {
					updateAlertPlaceholderError(result.message);
				}
			} catch (error) {
				console.error('Error:', error);
			}
		}

		if (event.target.matches("#password-change-form")) {
			event.preventDefault();
			const currentPassword = document.getElementById("current-password").value;
			const newPassword = document.getElementById("new-password").value;
			const confirmNewPassword = document.getElementById("confirm-new-password").value;

			try {
				const response = await fetch('/auth/change_password/', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						'X-CSRFToken': getCookie('csrftoken'),
						"Authorization": "Bearer " + localStorage.getItem("auth_token")
					},
					body: JSON.stringify({ old_password: currentPassword, new_password: newPassword, confirm_new_password: confirmNewPassword }),
					credentials: 'include'
				});

				const result = await response.json();
				if (result.status === 1) {
					successAlertPlaceholder(result.message);
				} else {
					updateAlertPlaceholderError(result.message);
				}
			} catch (error) {
				console.error('Error:', error);
			}
		}
	});
});


function getCookie(name) {
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

function updateAlertPlaceholderError(message) {
	var alertPlaceholder = document.getElementById('alert-placeholder');
	alertPlaceholder.innerHTML = `
		<div class="error-banner" role="alert">
			${escapeHtml(message)}
		</div>
	`;
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
	successAlert.classList.add('fade-out');
	successAlert.addEventListener('transitionend', () => {
		successAlert.remove();
	});
}, 3500);
}