class OnlineTournamentGameState {
	constructor(context, game, prevState) {
		this.disconnectOverlay = new DisconnectOverlay();
		this.gameEndState = new GameEndedState(
			game, context, prevState, this);
		this.playingState = new PlayingState(
			game, context, this, this.gameEndState);
		this.game = game;
		this.prevState = prevState;
		this.cancelBtn = document.createElement('button');
		this.cancelBtn.textContent = 'Cancel';
		this.cancelBtn.className = "btn btn-outline-light mb-2 w-100 h-100";

		this.cancelBtn.addEventListener('click', () => this.cancel());
		this.context = context;
	};
	cancel() {
		this.disconnectOverlay.hide();
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
		this.context.loadingOverlay.style.display = 'none';
		this.context.gameUI.style.display = 'flex'
		this.context.state = this.prevState;
		this.context.state.execute();
	}
	execute() {
		// Clear the game menu content
		this.context.gameUI.style.display = 'flex';
		this.context.gameMenu.style.display = 'none';
		this.context.overlayBody.innerHTML = '';
		this.context.loadingOverlay.style.display = 'flex';
		this.context.overlayBody.appendChild(this.cancelBtn);
		this.joinTournament();
	};

	handleEvent(event) {
		if (JSON.parse(event.data).status == "ready") {
			this.context.canvas.style.display = "";
			this.context.loadingOverlay.style.display = 'none';
			this.context.gameUI.style.display = 'none';
			this.context.state = this.playingState;
			this.context.state.execute();
			this.game.start(this.socket);
		}
	}

	update(data) {
		if (this.disconnectOverlay.handle(data))
			return;
		if (data.type == "end") {
			this.disconnectOverlay.hide();
			this.context.canvas.style.display = "none";
			const opponent1 = document.getElementById("opponent1");
			const opponent2 = document.getElementById("opponent2");
			opponent1.innerHTML = "";
			opponent2.innerHTML = "";
			if (data.status == "lost") {
				this.gameStatus = "ended";
				this.gameEndState.setMessage(data.player_name);
				if (this.socket) {
					this.socket.close();
					this.socket = null;
				}
				this.context.players.clear();
				this.context.state = this.gameEndState;
				this.context.state.execute();
				return;
			}
			if (data.status == "win") {
				if (data.context == "round") {
					this.context.gameUI.style.display = 'flex'
					this.context.state = this;
					this.execute();
					return;
				}
				this.gameStatus = "ended";
				this.gameEndState.setMessage(data.player_name);
				if (this.socket) {
					this.socket.close();
					this.socket = null;
				}
				this.context.players.clear();
				this.context.state = this.gameEndState;
				this.context.state.execute();
				return;
			}
		}
		else if (data.type == "tournament.players") {
			this.context.players.addPlayers(data.values);
			return;
		}
		else if (data.type == "room.players") {
			if (data.values.length == 2) {
				opponent1.textContent = data.values[0].player_name;
				opponent2.textContent = data.values[1].player_name;
				if (this.game.name === "snake")
					opponent2.className = "text-success";
				else
					opponent2.className = "text-dark";
			}
			return;
		}
		this.game.update(data);
	}

	joinTournament() {
		if (this.socket) {
			this.socket.close();
			this.socket = null;
		}
		// create a game and connect to socket.
		fetch("/games/join_tournament/", {
			method: "POST",
			headers: {
				"X-CSRFToken": getCookie("csrftoken"),
				"Authorization": "Bearer " + localStorage.getItem("auth_token")
			},
			credentials: "include",
			body: JSON.stringify({
				"game": this.game.name
			})
		})
		.then((response) => {
			if (!response.ok) {
				throw new Error(response.status);
			}
			return response.json();
		})
		.then(data => {
			this.socket = new WebSocket(`wss://${data.ip_address}/ws/game/${this.game.name}/${data.game_room_id}/?csrf_token=${getCookie("csrftoken")}&token=${localStorage.getItem("auth_token")}`);
			if (this.socket.readyState > this.socket.OPEN) {
				this.cancel();
				throw new Error("WebSocket error: " + this.socket.readyState);
			}
			this.socket.addEventListener("open", () => {
				this.playingState.bindSocket(this.socket);
				this.socket.addEventListener("message", (event) => {
					this.handleEvent(event);
				});
			});
		})
		.catch((error) => {
			this.cancel();
		});
	}
}
