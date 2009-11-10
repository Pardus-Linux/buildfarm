#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2009 TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Please read the COPYING file.

import os
import sys
import socket
import smtplib

import pisi.specfile

from buildfarm import config,logger,templates
config = config.Config()

try:
    import mailauth
except ImportError:
    # FIXME: Anddddd problem here
    if config.sendemail and config.usesmtpauth:
        logger.info("*** You have to create a mailauth.py file for defining 'username' and 'password' to use SMTP authentication.")
        sys.exit(1)

class MailerError(Exception):
    pass


def send(message, pspec = "", type = ""):

    def wrap(message, length=72):
        return reduce(lambda line, word: "%s%s%s" %
                      (line,
                       [" ", "\n"][(len(line)-line.rfind("\n")-1 + len(word.split("\n",1)[0]) >= length)],
                       word),
                      message.split(" "))

    if not config.sendemail:
        logger.info("*** Sending of notification e-mails is turned off.")
        return

    if config.usesmtpauth:
        if globals().has_key('mailauth'):
            if not mailauth.username or not mailauth.password:
                logger.info("*** You have to define username/password in mailauth.py for sending authenticated e-mails.")
                return

    recipientsName, recipientsEmail = [], []
    if pspec:
        specFile = pisi.specfile.SpecFile()
        specFile.read(os.path.join(config.localpspecrepo, pspec))
        recipientsName.append(specFile.source.packager.name)
        recipientsEmail.append(specFile.source.packager.email)

    templates = {"error"    : templates.error_message,
                 "info"     : templates.info_message,
                 "announce" : templates.announce_message}

    packagename = os.path.basename(os.path.dirname(pspec))
    last_log = "".join(open(config.logfile).readlines()[-20:])
    message = templates.get(type) % {'log'          : wrap(last_log),
                                     'recipientName': " ".join(recipientsName),
                                     'mailTo'       : ", ".join(recipientsEmail),
                                     'ccList'       : ', '.join(config.cclist),
                                     'mailFrom'     : config.mailfrom,
                                     'announceAddr' : config.announceaddr,
                                     'subject'      : pspec or type,
                                     'message'      : wrap(message),
                                     'pspec'        : pspec,
                                     'type'         : type,
                                     'packagename'  : packagename}

    # timeout value in seconds
    socket.setdefaulttimeout(10)

    try:
        session = smtplib.SMTP(config.smtpserver)
    except:
        logger.error("*** Failed sending e-mail: Couldn't open session on %s." % config.smtpserver)
        return

    if config.usesmtpauth and mailauth.password:
        try:
            session.login(mailauth.username, mailauth.password)
        except smtplib.SMTPAuthenticationError:
            logger.error("*** Failed sending e-mail: Authentication failed.")
            return

    try:
        if type == "announce":
            smtpresult = session.sendmail(config.mailfrom, config.announceaddr, message)
        else:
            smtpresult = session.sendmail(config.mailfrom, recipientsEmail + config.cclist, message)
    except smtplib.SMTPRecipientsRefused:
        logger.error("*** Failed sending e-mail: Recipient refused probably because of a non-authenticated session.")

def error(message, pspec):
    send(message, pspec, type = "error")

def info(message):
    send(message, type = "info")

def announce(message):
    send(message, type = "announce")
