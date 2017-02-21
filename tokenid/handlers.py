import names as namegenerator
import regex
import json
import blockies

from asyncbb.handlers import BaseHandler
from asyncbb.database import DatabaseMixin
from asyncbb.errors import JSONHTTPError
from tokenservices.handlers import RequestVerificationMixin
from tornado.escape import json_encode
from tornado.web import HTTPError


def validate_username(username):
    return regex.match('^[a-zA-Z][a-zA-Z0-9_]{2,59}$', username)

def user_row_for_json(row):
    rval = {
        'username': row['username'],
        'owner_address': row['eth_address'],
        'custom': json.loads(row['custom']) if isinstance(row['custom'], str) else (row['custom'] or {}),
        'is_app': row['is_app']
    }
    if rval['custom'] is None:
        rval['custom'] = {}
    if 'avatar' not in rval['custom']:
        rval['custom']['avatar'] = "/identicon/{}.png".format(row['eth_address'])
    return rval

def parse_boolean(b):
    if isinstance(b, str):
        b = b.lower()
        if b == 'true':
            return True
        elif b == 'false':
            return False
        else:
            return None
    elif isinstance(b, int):
        return bool(b)
    return None

class UserMixin(RequestVerificationMixin):

    async def update_user(self, address):

        payload = self.json

        async with self.db:

            # make sure a user with the given address exists
            user = await self.db.fetchrow("SELECT * FROM users WHERE eth_address = $1", address)
            if user is None:
                raise JSONHTTPError(404, body={'errors': [{'id': 'not_found', 'message': 'Not Found'}]})

            if not any(x in payload for x in ['username', 'custom']):
                raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})

            if 'username' in payload and user['username'] != payload['username']:
                username = payload['username']
                if not validate_username(username):
                    raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_username', 'message': 'Invalid Username'}]})

                # make sure the username isn't used by a different user
                row = await self.db.fetchrow("SELECT * FROM users WHERE username = $1", username)
                if row is not None:
                    raise JSONHTTPError(400, body={'errors': [{'id': 'username_taken', 'message': 'Username Taken'}]})

                await self.db.execute("UPDATE users SET username = $1 WHERE eth_address = $2", username, address)
            else:
                username = user['username']

            if 'custom' in payload:
                custom = payload['custom']

                await self.db.execute("UPDATE users SET custom = $1 WHERE eth_address = $2", json_encode(custom), address)
            else:
                custom = user['custom']

            if 'is_app' is payload:
                is_app = parse_boolean(payload['is_app'])
                if not isinstance(is_app, bool):
                    raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})
                await self.db.execute("UPDATE users SET is_app = $1 WHERE eth_address = $2", is_app, address)
            else:
                is_app = user['is_app']

            await self.db.commit()

        if 'avatar' not in custom:
            custom['avatar'] = "/identicon/{}.png".format(address)
        self.write({
            'username': username,
            'owner_address': address,
            'custom': custom,
            'is_app': is_app
        })


class UserCreationHandler(UserMixin, DatabaseMixin, BaseHandler):

    async def post(self):

        address = self.verify_request()
        payload = self.json

        # check if the address has already registered a username
        async with self.db:
            row = await self.db.fetchrow("SELECT * FROM users WHERE eth_address = $1", address)
        if row is not None:
            raise JSONHTTPError(400, body={'errors': [{'id': 'already_registered', 'message': 'The provided address is already registered'}]})

        if 'username' in payload:

            username = payload['username']

            if not validate_username(username):
                raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_username', 'message': 'Invalid Username'}]})

            # check username doesn't already exist
            async with self.db:
                row = await self.db.fetchrow("SELECT * FROM users WHERE lower(username) = lower($1)", username)
            if row is not None:
                raise JSONHTTPError(400, body={'errors': [{'id': 'username_taken', 'message': 'Username Taken'}]})

        else:

            # generate temporary username
            while True:
                username = ''.join(namegenerator.get_full_name().split())
                async with self.db:
                    row = await self.db.fetchrow("SELECT * FROM users WHERE lower(username) = lower($1)", username)
                if row is None:
                    break

        custom = {}
        if 'custom' in payload:
            custom = payload['custom']
        # set default avatar
        if 'avatar' not in custom:
            custom['avatar'] = "/identicon/{}.png".format(address)

        if 'is_app' in payload:
            is_app = parse_boolean(payload['is_app'])
            if is_app is None:
                raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})
        else:
            is_app = False

        async with self.db:
            await self.db.execute("INSERT INTO users (username, eth_address, custom, is_app) VALUES ($1, $2, $3, $4)",
                                  username, address, json_encode(custom), is_app)
            await self.db.commit()

        self.write({
            'username': username,
            'owner_address': address,
            'custom': custom,
            'is_app': is_app
        })

    def put(self):

        address = self.verify_request()
        return self.update_user(address)

class UserHandler(UserMixin, DatabaseMixin, BaseHandler):

    async def get(self, username):

        # check if ethereum address is given
        if regex.match('^0x[a-fA-F0-9]{40}$', username):

            async with self.db:
                row = await self.db.fetchrow("SELECT * FROM users WHERE eth_address = $1", username)

        # otherwise verify that username is valid
        elif not regex.match('^[a-zA-Z][a-zA-Z0-9_]{2,59}$', username):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_username', 'message': 'Invalid Username'}]})

        else:
            async with self.db:
                row = await self.db.fetchrow("SELECT * FROM users WHERE lower(username) = lower($1)", username)

        if row is None:
            raise JSONHTTPError(404, body={'errors': [{'id': 'not_found', 'message': 'Not Found'}]})

        self.write(user_row_for_json(row))

    async def put(self, username):

        if regex.match('^0x[a-fA-F0-9]{40}$', username):

            address_to_update = username

        elif regex.match('^[a-zA-Z][a-zA-Z0-9_]{2,59}$', username):

            async with self.db:
                row = await self.db.fetchrow("SELECT * FROM users WHERE lower(username) = lower($1)", username)
            if row is None:
                raise JSONHTTPError(404, body={'errors': [{'id': 'not_found', 'message': 'Not Found'}]})

            address_to_update = row['eth_address']

        else:

            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_username', 'message': 'Invalid Username'}]})

        request_address = self.verify_request()

        if request_address != address_to_update:

            raise JSONHTTPError(401, body={'errors': [{'id': 'permission_denied', 'message': 'Permission Denied'}]})

        return await self.update_user(address_to_update)


class SearchUserHandler(UserMixin, DatabaseMixin, BaseHandler):

    async def get(self):

        try:
            offset = int(self.get_query_argument('offset', 0))
            limit = int(self.get_query_argument('limit', 10))
        except ValueError:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})

        query = self.get_query_argument('query', None)
        apps = parse_boolean(self.get_query_argument('apps', None))

        if query is None:
            results = []
        else:
            args = [offset, limit]
            sql = "SELECT * FROM users WHERE username ILIKE $3"
            args.append('%' + query + '%')
            if apps is not None:
                sql += " AND is_app = $4"
                args.append(apps)
            sql += " ORDER BY username OFFSET $1 LIMIT $2"

            async with self.db:
                rows = await self.db.fetch(sql, *args)
            results = [user_row_for_json(row) for row in rows]
        querystring = 'query={}'.format(query)
        if apps is not None:
            querystring += '&apps={}'.format('true' if apps else 'false')

        self.write({
            'query': querystring,
            'offset': offset,
            'limit': limit,
            'results': results
        })

class IdenticonHandler(BaseHandler):

    FORMAT_MAP = {
        'PNG': 'image/png',
        'JPG': 'image/jpeg'
    }

    def get(self, address, format):
        format = format.upper()
        if format not in self.FORMAT_MAP.keys():
            raise HTTPError(404)
        data = blockies.create(address, size=8, scale=12, format=format.upper())
        self.set_header("Content-type", self.FORMAT_MAP[format])
        self.set_header("Content-length", len(data))
        self.write(data)
