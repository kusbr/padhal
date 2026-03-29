create a wordle game using python
write tests
can you make this real world by connecting to a free yet known online dictionary
add tests for the new changes
make the hidden answer word come from an online source too, instead of only validating guesses online
when user enters 5 letter word it shows this error "Guess is not recognized by the dictionary."
why did live api fail
we should use a known reliable language dictionary to both get a word and validate inputs. Otherwise it will not scale and will become predictable. can we interact with the https://api.dictionaryapi.dev and parse its json response
use the api to both generate and validate
should use the api to generate also but with a local fallback only for 10%
in terminal show if the word was picked locally or from api
continuously shows "Unable to fetch word from API" but the api seems to work when I tried
are there other api that can get a list of valid common 5 letter words randomly or by taking a starting alphabet or a part of speech as input
back to same error "Unable to fetch a valid answer word from the API."
Unable to validate API candidate 'perch': HTTP Error 403: Forbidden
now refactor the code so that it exposes an API consumed by a frontend
make it runnable on any machine i.e. use 0.0.0.0
make this as three layered architecture - 1. front end 2. API layer 3. repository using industry standard patterns to segregate concerns. The repository will connect to datamuse and dictionary api
found one bug - if user types an invalid English word the game accepts it and shows. Rather it should not accept invalid English word
instead of every time asking the user to create a game, if its a new session auto create the game but dont show on screen
do not show the following on the UI "Frontend for the local JSON API. Create a game, submit guesses, and render the board in the browser." "GameID" panel and remove status and source also
make it scalable to allow multiuser, multithread ready
lets make it containerized
make the front end and api as separate containers
on the UI allow user to type anywhere and display. ENTER should submit. remove the textbox its label and the submit button
if the word has been already guessed do not accept it and show a message. make all messages as an overlay
create kubernetes manifests to deploy this to any k8s cluster
Brand the game as "Padhal" a blend of sanskrit "padam" and "wordle" also display sanskrit padhal in UI. change all service names to padhal in code
rename docker images and container names as padhal-* imstead of codex-*
make this solution highly scalable by adding redis cache container if needed
add a disclaimer
make ux mobile ready
push code to git repo https://github.com/kusbr/padhal
push the code to git. exclude these folders  - __pycache__, foundry and any files with secrets keys
add a readme
add gitaction to build docker images and push to kumsub/padhal. the hub.docker.com uses username kumsub and password and 2FA
push these changes
buildx failed with: ERROR: failed to build: failed to solve: failed to fetch oauth token: unexpected status from GET request to
As suggested I added the secret vars to git repo settings
have added the PAT generated on docker hub
401 for token.. how to add push pull permissions on docker hub for token
updated PAT on docker hub to have RWD scope
now ensure docker-compose and Kubernetes use the latest image published by the action
do not use latest tag. use other
create a helm deployment with values and replace the image tag with the action commit sha
deploy using helm to docker-desktop Kubernetes cluster
push latest changes to git
what would be the daily cost of running this on azure in a container app with 0.5 CPU southindia 1GB 1 replica, in INR monthly azure cost
can you move all source code under src folder
Error response from daemon: failed to resolve reference "docker.io/kumsub/padhal-api:replace-me": docker.io/kumsub/padhal-api:replace-me: not found
move all docker files to docker folder
push changes to git
the three containers - frontend, api and redis be deployed to same azure container app
create a bicep template to create azure container app and deploy the solution to a single container app
Ensure the same word is not selected again within a known time period say 1 month
instead of raising an error if no word could be found, reset the timewindow
Add a link in UI to start a new game, refresh inline and start a new game
In the disclaimer indicate that this is a kind of copy of the Wordle game just for fun  Also mention Padhal is derived from sanskrit padam + wordle
on mobile the cursor seems visible at odd fields
push to git
add infra also to git since it includes bicep templates to deploy to azure
add an user assigned identity to the container app in the infra bicep template. create a container registry bicep in the same rg. update the git action to publish docker image to this acr also. Update padhal container app to pull latest tag image from this acr
docker (kumsub/padhal-frontend, padhal-frontend, docker/Dockerfile.frontend)
  Login failed with Error: The process '/usr/bin/az' failed with exit code 1. Double check if the 'auth-type' is correct. Refer to https://github.com/
  Azure/login#readme for more information.
lets go with FIC
add these changes to infra bicep templates
push to git




