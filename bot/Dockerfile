FROM python:3.10-bookworm

# Copy just what's required to do a `pip install`, because that's what's going to take time.
# Hence, docker will cache this step and the next step.
# If we'd copied the whole directory here, __any__ change in that directory would bust the cache
# and force docker to do `pip install` again.
COPY ./pyproject.toml /bot/pyproject.toml

RUN pip install --no-cache-dir /bot

COPY . /bot

WORKDIR /
