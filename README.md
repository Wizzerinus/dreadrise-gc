# Dreadrise

Repository for the Dreadrise website used in the Penny Dreadful community and
the MSE Modern community.

## Development setup

* Install python 3.9 (if you have asdf or pyenv you can get that automatically)
  * Should probably work on 3.8 and 3.10 too
* Run `pipenv install --dev`
* Create a MongoDB database for each distribution you're planning to use.
  They can be on the same or different clusters.
* Put the connection string into the `config/dist/<dname>/secrets.yml` file like this:
  `MONGODB_URL: mongodb+srv://user:password@mongo_url/db_name`
* Run `pipenv run python run.py website --debug` to run the website.
  * By default, runs on `localhost:3002`
  * `--debug` enables automatic reload of the Python code and of templates.
* After you're finished development, run `pipenv run python dev.py complete`
  to sort imports and lint the code.

## Configuration files explanation
* Each directory (`config` as well as `config/dist/<dname>`) can have up to two
  files: `core.yml` and `secrets.yml`.
* Secrets are ignored from version control.
* In the same directory, the secrets override the core settings.
* Between directories, the distribution directory overrides the main directory.
  * Some configuration variables cannot be overridden by distributions.
* In addition, environmental variables override the secrets.
  * Envs with the name `default__VAR` override the default ones. (Note the
    double underscore)
  * Envs with the name `dname__VAR` override the ones for a given distribution.
* The configuration options:
  * Can be overridden by distributions
    * `BRAND` - has the title which is shown on the website
    * `MONGODB_URL` - the database connection string (see above)
    * `gateway_key` - used for external POST requests to `/api/gateway`
    * `allow_disk_use` - set this to any non-empty string to allow disk usage when
      using search. Can accelerate some searches, but does not work on free 
      Atlas clusters.
      * Currently, does not do anything (after the search optimizations). 
  * Cannot be overridden
    * `DISCORD_CLIENT_ID` - used for logins
    * `DISCORD_CLIENT_SECRET` - used for logins
    * `session_backend` - can be either `flask` or `firestore`. `firestore` enables
      the session to be stored in the Google Firestore database. Requires the
      installation of Google python package.
      * Good luck figuring where it takes the secrets from because idr lol
    * `secret_key` - the cookie key, used for cookie validation
    * `PORT` - the port the application is run on when using `run.py website`
    * `repo_location` - the repository location, used for the update gateway
