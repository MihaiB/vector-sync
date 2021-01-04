FROM docker.io/library/python
RUN ["useradd", "--create-home", "user"]
USER user:user
RUN ["mkdir", "/home/user/vector-sync"]
WORKDIR /home/user/vector-sync
COPY --chown=user:user [".", "."]
RUN ["./docker.sh"]
