#!/usr/bin/env python
import sys
import os
import pymongo

# PRECEDENCE:
#  CLI
#  ENV
#  DEFAULT

if __name__ == "__main__":

  # Set default
  dbhost = "127.0.0.1"
  dbport = 27017

  # ENV takes precedence over default
  if 'DB_SERVICE_HOST' in os.environ: dbhost = os.environ['DB_SERVICE_HOST']
  if 'DB_SERVICE_PORT' in os.environ: dbport = int(os.environ['DB_SERVICE_PORT'])

  # CLI takes precedence over all
  if len(sys.argv) > 1: dbhost = sys.argv[1]
  if len(sys.argv) > 2: dbport = int(sys.argv[2])

  print "Testing connection to MongoDB on %s, %s" % (dbhost, dbport)
  try:
    connection = pymongo.Connection(dbhost, int(dbport))
  except:
    sys.exit(1)

