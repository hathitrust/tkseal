#!/bin/bash

# set up minikube & get sealed secrets installed

if ! command -v minikube; then
  echo ❌  minikube is not installed
  exit 1
else
  echo ✅  minikube is installed
fi

if ! minikube start; then
  echo 😕  minikube failed to start
  exit 1
fi

echo ⚙️  checking kubectl context
current_context=$(minikube kubectl config current-context)
if [[ "$current_context" != "minikube" ]]; then
  echo 😕  current context is $current_context, not minikube - something is wrong
  exit 1
else
  echo ✅  kubectl is accessing minikube
fi

echo 🔒 installing sealed secrets

echo minikube kubectl apply -- -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.32.2/controller.yaml

####### outline of integration tests

echo ⚙️  setting up tanka environment
mkdir sealedsecret-test
cd sealedsecret-test
tk init --k8s 1.33

apiserver=$(minikube kubectl -- cluster-info | grep 'Kubernetes control plane is running at' | awk '{print $NF}')
tk env set environments/default --server=$apiserver

# tkseal pull
# create a secret:
minikube kubectl -- create secret generic testsecret --from-literal "testvalue=mashed_potatoes"
tkseal pull ./environments/default/
# should show the secret testsecret/mashed_potatoes
# plain_secrets.json should have the secret
minikube kubectl -- delete secret testsecret


# tkseal seal
cat<<EOT > environments/default/plain_secrets.json
[
  {
    "name": "testsecret",
    "data": {
      "testvalue": "baked_potatoes"
    }
  }
]
EOT
tkseal seal ./environments/default/
# should show a diff with testsecret
# should have sealed_secrets.json with expected json

cat<<EOT > environments/default/main.jsonnet
{ secrets: import 'sealed_secrets.json' }
EOT

tk apply ./environments/default/
# diff should show the new sealedsecret

minikube kubectl -- get -o jsonpath={.data.testvalue} secret testsecret | base64 -d
# should be baked_potatoes



# tkseal diff
# after doing tkseal seal and having a sealed secret on the cluster
# make sure we see a sealedsecret with kubectl

cat<<EOT > environments/default/plain_secrets.json
[
  {
    "name": "testsecret2",
    "data": {
      "testvalue": "fried_potatoes"
    }
  }
]
EOT

# tk diff should show:

# -      "testvalue": "baked_potatoes"
# +      "testvalue": "fried_potatoes"
