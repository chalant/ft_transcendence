all: build up

detached: build upd

build:
	docker compose -f src/docker-compose.yaml build

up:
	docker compose -f src/docker-compose.yaml up

upd:
	docker compose -f src/docker-compose.yaml up -d

down:
	docker compose -f src/docker-compose.yaml down

clean: down

fclean: clean
	docker system prune -af
	docker volume prune -f

# Kubernetes (k3s): import the locally built images, then install the chart.
K8S_IMAGES = proxy-server-image users-image website-image game-server-image postgresql-image
K8S_NAMESPACE = transcendence
CHART = helm/ft-transcendence

k3s-images: build
	docker save $(K8S_IMAGES) | sudo k3s ctr images import -

helm-install:
	helm upgrade --install transcendence $(CHART) \
		-n $(K8S_NAMESPACE) --create-namespace -f $(CHART)/values-k3s.yaml

helm-uninstall:
	helm uninstall transcendence -n $(K8S_NAMESPACE)

.PHONY: all detached build up upd down clean fclean k3s-images helm-install helm-uninstall
