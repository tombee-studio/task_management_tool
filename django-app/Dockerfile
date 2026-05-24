FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target ${LAMBDA_TASK_ROOT}

COPY . .

ARG GIT_HASH=unknown
ENV GIT_HASH=$GIT_HASH

CMD ["lambda_handler.handler"]
