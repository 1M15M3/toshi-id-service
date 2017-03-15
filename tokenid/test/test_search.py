import os
import names as namegen
from tornado.escape import json_decode, json_encode
from tornado.testing import gen_test

from tokenid.app import urls
from tokenservices.test.base import AsyncHandlerTest
from asyncbb.test.database import requires_database
from ethutils import data_encoder, private_key_to_address

from urllib.parse import quote_plus

from tokenid.test.test_user import TEST_PRIVATE_KEY, TEST_ADDRESS, TEST_PAYMENT_ADDRESS

class SearchUserHandlerTest(AsyncHandlerTest):

    def get_urls(self):
        return urls

    def fetch(self, url, **kwargs):
        return super(SearchUserHandlerTest, self).fetch(url, **kwargs)

    def get_url(self, path):
        path = "/v1{}".format(path)
        return super().get_url(path)

    @gen_test
    @requires_database
    async def test_username_query(self):

        username = "bobsmith"
        positive_query = 'bobsm'
        negative_query = 'nancy'

        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, token_id) VALUES ($1, $2)", username, TEST_ADDRESS)

        resp = await self.fetch("/search/user?query={}".format(positive_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 1)

        resp = await self.fetch("/search/user?query={}".format(negative_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

    @gen_test
    @requires_database
    async def test_invalid_username_query(self):

        username = "bobsmith"
        invalid_query = quote_plus('!@#$')

        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, token_id) VALUES ($1, $2)", username, TEST_ADDRESS)

        resp = await self.fetch("/search/user?query={}".format(invalid_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

    @gen_test
    @requires_database
    async def test_username_query_sql_inject_attampt(self):

        username = "bobsmith"
        inject_attempt = quote_plus("x'; delete from users; select * from users")

        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, token_id) VALUES ($1, $2)", username, TEST_ADDRESS)

        resp = await self.fetch("/search/user?query={}".format(inject_attempt), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

        async with self.pool.acquire() as con:
            row = await con.fetchrow("SELECT COUNT(*) AS count FROM users")

        self.assertEqual(row['count'], 1)

    @gen_test
    @requires_database
    async def test_bad_limit_and_offset(self):

        positive_query = 'bobsm'

        resp = await self.fetch("/search/user?query={}&offset=x".format(positive_query), method="GET")
        self.assertEqual(resp.code, 400)

        resp = await self.fetch("/search/user?query={}&limit=x".format(positive_query), method="GET")
        self.assertEqual(resp.code, 400)

    @gen_test
    @requires_database
    async def test_limit_and_offset(self):

        username = "bobsmith"
        address = int(TEST_ADDRESS[2:], 16)
        num_of_users = 170

        async with self.pool.acquire() as con:
            # creates a bunch of users with numbering suffix to test limit and offset
            # insert users in reverse order to assure that search results are returned in alphabetical order
            for i in range(num_of_users - 1, -1, -1):
                await con.execute("INSERT INTO users (username, token_id) VALUES ($1, $2)",
                                  # make sure the suffix is always the same length to ensure it's easy to match alphabetical ordering
                                  "{0}{1:0{2}}".format(username, i, len(str(num_of_users))),
                                  # makes sure every user has a different eth address
                                  "{0:#0{1}x}".format(address + i, 42))

        positive_query = 'bobsm'
        test_limit = 30

        for i in range(0, num_of_users, test_limit):
            resp = await self.fetch("/search/user?query={}&limit={}&offset={}".format(positive_query, test_limit, i), method="GET")
            self.assertEqual(resp.code, 200)
            body = json_decode(resp.body)
            self.assertEqual(len(body['results']), min(i + test_limit, num_of_users) - i)
            j = i
            for res in body['results']:
                self.assertEqual(res['username'], "{0}{1:0{2}}".format(username, j, len(str(num_of_users))))
                j += 1

    @gen_test
    @requires_database
    async def test_only_apps_query(self):

        data_encoder, private_key_to_address
        users = [
            ('bob{}'.format(i), private_key_to_address(data_encoder(os.urandom(32))), False)
            for i in range(6)
        ]
        bots = [
            ('bot{}'.format(i), private_key_to_address(data_encoder(os.urandom(32))), True)
            for i in range(4)
        ]

        async with self.pool.acquire() as con:
            for args in users + bots:
                await con.execute("INSERT INTO users (username, token_id, is_app) VALUES ($1, $2, $3)", *args)

        resp = await self.fetch("/search/user?query=bo", method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 10)

        resp = await self.fetch("/search/user?query=bo&apps=false", method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 6)

        resp = await self.fetch("/search/user?query=bo&apps=true", method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 4)

    @gen_test
    @requires_database
    async def test_name_query(self):

        username = "user231"
        name = "Bobby"
        positive_query = 'bob'
        negative_query = 'nancy'

        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, token_id, name) VALUES ($1, $2, $3)",
                              username, TEST_ADDRESS, name)

        resp = await self.fetch("/search/user?query={}".format(positive_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 1)

        resp = await self.fetch("/search/user?query={}".format(negative_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

    # def get_app(self):
    #     self._config['database'] = {'dsn': 'postgresql://token@127.0.0.1/token-id'}
    #     app = super().get_app()
    #     self.pool = app.connection_pool
    #     return app

    @gen_test(timeout=300)
    @requires_database
    async def test_fulltextsearch(self):
        no_of_users_to_generate = 100
        insert_vals = [(private_key_to_address(os.urandom(32)), "user0", "Bob Smith")]
        some_bobs = False
        for i in range(1, no_of_users_to_generate):
            key = os.urandom(32)
            while True:
                name = namegen.get_full_name()
                # make sure we never generate any user's called bob
                if 'Bob' in name or 'bob' in name:
                    continue
                break
            # give ten of the users a 'bob##' username
            if i % (no_of_users_to_generate / 10) == 0:
                some_bobs = True
                username = 'bob{}'.format(i)
            else:
                username = 'user{}'.format(i)
            #resp = await self.fetch_signed(
            #    "/user", method="POST", signing_key=key,
            #    body=body)
            #self.assertEqual(resp.code, 200)
            insert_vals.append((private_key_to_address(key), username, name))
        async with self.pool.acquire() as con:
            await con.executemany(
                "INSERT INTO users (token_id, username, name) VALUES ($1, $2, $3)",
                insert_vals)
            count = await con.fetchrow("SELECT count(*) FROM users")
            bobcount = await con.fetchrow("SELECT count(*) FROM users where username ilike 'bob%'")
        self.assertTrue(count['count'] > 0)
        self.assertTrue(bobcount['count'] > 0)
        self.assertTrue(some_bobs)
        resp = await self.fetch("/search/user?query=bob", method="GET")
        self.assertEqual(resp.code, 200)
        results = json_decode(resp.body)['results']
        self.assertTrue(len(results) > 1)
        # make sure that name is prefered over username
        self.assertEqual(results[0]['name'], "Bob Smith")
        self.assertTrue(results[1]['username'].startswith("bob"))
