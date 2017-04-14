from tornado.escape import json_decode
from tornado.testing import gen_test

from tokenid.app import urls
from tokenservices.test.base import AsyncHandlerTest
from tokenservices.test.database import requires_database

TEST_ADDRESS = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"

class AppsHandlerTest(AsyncHandlerTest):

    def get_urls(self):
        return urls

    def get_url(self, path):
        path = "/v1{}".format(path)
        return super().get_url(path)

    @gen_test
    @requires_database
    async def test_get_app_index(self):
        resp = await self.fetch("/apps/", method="GET")
        self.assertResponseCodeEqual(resp, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

        setup_data = [
            ("TokenBotA", TEST_ADDRESS[:-1] + 'f', False),
            ("TokenBotB", TEST_ADDRESS[:-1] + 'e', False),
            ("FeaturedBotA", TEST_ADDRESS[:-1] + 'd', True),
            ("FeaturedBotB", TEST_ADDRESS[:-1] + 'c', True),
            ("FeaturedBotC", TEST_ADDRESS[:-1] + 'b', True)
        ]

        for username, addr, featured in setup_data:
            async with self.pool.acquire() as con:
                await con.execute("INSERT INTO users (username, name, token_id, is_app, featured) VALUES ($1, $2, $3, $4, $5)",
                                  username, username, addr, True, featured)

        resp = await self.fetch("/apps", method="GET")
        self.assertResponseCodeEqual(resp, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 5)

        # test /apps/featured
        resp = await self.fetch("/apps/featured", method="GET")
        self.assertResponseCodeEqual(resp, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 3)

        resp = await self.fetch("/apps?featured", method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 3)

        for true in ['', 'true', 'featured', 'TRUE', 'True']:

            resp = await self.fetch("/apps?featured={}".format(true), method="GET")
            self.assertEqual(resp.code, 200)
            body = json_decode(resp.body)
            self.assertEqual(len(body['results']), 3, "Failed to map featured={} to true".format(true))

        for false in ['false', 'FALSE', 'False']:

            resp = await self.fetch("/apps?featured={}".format(false), method="GET")
            self.assertEqual(resp.code, 200)
            body = json_decode(resp.body)
            self.assertEqual(len(body['results']), 5, "Failed to map featured={} to false".format(false))

    @gen_test
    @requires_database
    async def test_get_app(self):
        username = "TokenBot"
        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, name, token_id, is_app) VALUES ($1, $2, $3, $4)",
                              username, username, TEST_ADDRESS, True)
        resp = await self.fetch("/apps/{}".format(TEST_ADDRESS), method="GET")
        self.assertResponseCodeEqual(resp, 200)

    @gen_test
    @requires_database
    async def test_get_missing_app(self):
        resp = await self.fetch("/apps/{}".format(TEST_ADDRESS), method="GET")
        self.assertResponseCodeEqual(resp, 404)


class SearchAppsHandlerTest(AsyncHandlerTest):

    def get_urls(self):
        return urls

    def fetch(self, url, **kwargs):
        return super(SearchAppsHandlerTest, self).fetch("/v1{}".format(url), **kwargs)

    @gen_test
    @requires_database
    async def test_username_query(self):
        username = "TokenBot"
        positive_query = 'Tok'
        negative_query = 'TickleFight'

        async with self.pool.acquire() as con:
            await con.execute("INSERT INTO users (username, name, token_id, is_app) VALUES ($1, $2, $3, $4)",
                              username, username, TEST_ADDRESS, True)

        resp = await self.fetch("/search/apps?query={}".format(positive_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 1)

        resp = await self.fetch("/search/apps?query={}".format(negative_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 0)

    @gen_test
    @requires_database
    async def test_featured_query(self):

        positive_query = 'bot'

        setup_data = [
            ("TokenBotA", "token bot a", TEST_ADDRESS[:-1] + 'f', False),
            ("TokenBotB", "token bot b", TEST_ADDRESS[:-1] + 'e', False),
            ("FeaturedBotA", "featured token bot a", TEST_ADDRESS[:-1] + 'd', True),
            ("FeaturedBotB", "featured token bot b", TEST_ADDRESS[:-1] + 'c', True),
            ("FeaturedBotC", "featured token bot c", TEST_ADDRESS[:-1] + 'b', True)
        ]

        for username, name, addr, featured in setup_data:
            async with self.pool.acquire() as con:
                await con.execute("INSERT INTO users (username, name, token_id, featured, is_app) VALUES ($1, $2, $3, $4, $5)",
                                  username, name, addr, featured, True)

        resp = await self.fetch("/search/apps?query={}".format(positive_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 5)

        resp = await self.fetch("/search/apps?query={}&featured".format(positive_query), method="GET")
        self.assertEqual(resp.code, 200)
        body = json_decode(resp.body)
        self.assertEqual(len(body['results']), 3)

        for true in ['', 'true', 'featured', 'TRUE', 'True']:

            resp = await self.fetch("/search/apps?query={}&featured={}".format(positive_query, true), method="GET")
            self.assertEqual(resp.code, 200)
            body = json_decode(resp.body)
            self.assertEqual(len(body['results']), 3, "Failed to map featured={} to true".format(true))

        for false in ['false', 'FALSE', 'False']:

            resp = await self.fetch("/search/apps?query={}&featured={}".format(positive_query, false), method="GET")
            self.assertEqual(resp.code, 200)
            body = json_decode(resp.body)
            self.assertEqual(len(body['results']), 5, "Failed to map featured={} to false".format(false))

    @gen_test
    @requires_database
    async def test_bad_limit_and_offset(self):
        positive_query = 'enb'

        resp = await self.fetch("/search/apps?query={}&offset=x".format(positive_query), method="GET")
        self.assertEqual(resp.code, 400)

        resp = await self.fetch("/search/apps?query={}&limit=x".format(positive_query), method="GET")
        self.assertEqual(resp.code, 400)
