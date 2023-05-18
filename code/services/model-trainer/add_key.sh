#!/bin/bash
echo $SSH_PRIVATE | base64 -d >> /root/.ssh/id_rsa