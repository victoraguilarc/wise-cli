#!/bin/bash

PROJECT_NAME={{ project_name }}                                 # Application Name

PROJECT_PATH={{ project_path }}                             # Project path
PROJECT_CODE_PATH={{ project_code_path }}                             # Project path
PYTHON_ENV=${PROJECT_PATH}/env                              # Virtual environment path

SOCKET_PATH=/tmp                                            # Root socket path
SOCKET_FILE=${SOCKET_PATH}/${PROJECT_NAME}.socket               # Socket file path


USER={{ project_user }}
GROUP={{ project_group }}
NUM_WORKERS=3                                               # workers CPUs*2+1


BIND=unix:$SOCKET_FILE                                      # Socket to binding

echo "Starting $NAME as `whoami`"

source ${PROJECT_PATH}/env/bin/activate
cd ${PROJECT_CODE_PATH}

export DJANGO_SETTINGS_MODULE=config.settings.production
export DJANGO_READ_ENV_FILE=True
export PYTHONPATH=${PROJECT_CODE_PATH}:${PYTHONPATH}

# test if exist socket path
test -d ${SOCKET_PATH} || mkdir -p ${SOCKET_PATH}

# Execute django app
# Los programas que se ejecutaran bajo **supervisor** no deben demonizarse a si mismas (no usar --daemon)
exec ${PYTHON_ENV}/bin/gunicorn config.wsgi:application \
  --name=${PROJECT_NAME} \
  --workers ${NUM_WORKERS} \
  --user=${USER} --group=${GROUP} \
  --bind=${BIND} \
  --log-file=-
  # --log-level=debug \
