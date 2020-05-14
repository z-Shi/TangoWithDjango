from unittest.mock import patch, Mock, MagicMock, PropertyMock

import factory

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from faker import Factory

from rango.bing_search import BingSearchInternal
from rango.models import Category, Page


# Constants
NO_CATEGORIES_MESSAGE = 'There are no categories present.'
NO_PAGES_MESSAGE = 'There are no pages present.'
ENTER_CATEGORY_MESSAGE = 'enter the category name'
ENTER_PAGE_TITLE_MESSAGE = 'enter the title of the page'
ENTER_PAGE_URL_MESSAGE = 'enter the URL of the page'

# Factories for Faking
faker = Factory.create()


class CategoryFactory(factory.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.LazyAttribute(lambda _: faker.word())
    views = faker.random_int(min=0, max=100, step=1)
    likes = faker.random_int(min=0, max=100, step=1)


class PageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Page

    category = factory.SubFactory(CategoryFactory)
    title = " ".join(faker.words(nb=2, unique=True))
    url = faker.url()


# Side Effect Function
def side_effect_function(query):
    return [{'title': 'GitHub', 'link': 'https://www.github.com', 'summary': 'Remote Code'}]


# Login TestCase
class LoggedInTestCase(TestCase):

    def setUp(self):
        username = faker.profile()['username']
        password = faker.password()

        user = User.objects.create(username=username)
        user.set_password(password)
        user.save()

        self.client.login(username=username, password=password)


class LoggedOutTestCase(TestCase):
    pass


# Test Cases
class CategoryModelTests(LoggedOutTestCase):

    def test_views_positive(self):
        category = CategoryFactory(views=-1)

        self.assertTrue(category.views >= 0)

    def test_slug_creation(self):
        words = faker.words(nb=2, unique=True)

        category = CategoryFactory(name=" ".join(words))

        self.assertEqual(category.slug, "-".join(words).lower())


class PageModelTests(LoggedOutTestCase):

    def test_last_visit(self):
        category = CategoryFactory()
        page = PageFactory(category=category)

        self.assertTrue(timezone.now() >= page.last_visit)

    def test_last_visit_updated_by_goto(self):
        category = CategoryFactory()
        page = PageFactory(category=category)
        creation_date = page.last_visit

        self.client.get(reverse('rango:goto'), {'page_id': page.id})

        page.refresh_from_db()

        self.assertTrue(page.last_visit > creation_date)


class IndexViewTests(LoggedOutTestCase):

    def test_no_categories_or_pages(self):
        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, NO_CATEGORIES_MESSAGE)
        self.assertContains(response, NO_PAGES_MESSAGE)
        self.assertQuerysetEqual(response.context['categories'], [])
        self.assertQuerysetEqual(response.context['pages'], [])

    def test_categories_no_pages(self):
        categories = CategoryFactory.create_batch(3)

        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)

        for category in categories:
            self.assertContains(response, category.name)

        num_categories = len(response.context['categories'])
        self.assertEqual(num_categories, 3)

    def test_pages_and_categories(self):
        categories = CategoryFactory.create_batch(2)
        pages = []

        for category in categories:
            pages.append(PageFactory(category=category))

        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)

        for category in categories:
            self.assertContains(response, category.name)

        num_categories = len(response.context['categories'])
        self.assertEqual(num_categories, 2)

        for page in pages:
            self.assertContains(response, page.title)

        num_pages = len(response.context['pages'])
        self.assertEqual(num_pages, 2)


class AboutViewTests(LoggedOutTestCase):

    def test_visited(self):
        response = self.client.get(reverse('rango:about'))

        num_visits = response.context['visits']

        self.assertEquals(num_visits, 1)


class ShowCategoryViewTestsUsingStub(LoggedOutTestCase):

    def test_category_no_pages(self):
        category = CategoryFactory()

        response = self.client.get(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, category.name)
        self.assertContains(response, NO_PAGES_MESSAGE)
        self.assertQuerysetEqual(response.context['pages'], [])
        self.assertQuerysetEqual(response.context['result_list'], [])

    def test_category_with_pages(self):
        category = CategoryFactory()
        page = PageFactory(category=category)

        response = self.client.get(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))
        num_pages = len(response.context['pages'])

        self.assertEquals(response.status_code, 200)
        self.assertEquals(num_pages, 1)
        self.assertContains(response, category.name)
        self.assertContains(response, page.title)
        self.assertQuerysetEqual(response.context['result_list'], [])

    def test_category_not_logged_in(self):
        category = CategoryFactory()
        query = faker.word()

        response = self.client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                                    data={'query': query})

        self.assertRedirects(response, '/accounts/login/?next=/rango/category/' + category.slug + '/')

    def test_with_stubbed_api_call(self):
        category = CategoryFactory()
        query = faker.word()
        data = {'query': query, 'internal': True}

        username = faker.profile()['username']
        password = faker.password()

        user = User.objects.create(username=username)
        user.set_password(password)
        user.save()

        client = Client()
        client.login(username=username, password=password)

        response = client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                               data=data)
        results = response.context['result_list']

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(results), 1)
        self.assertContains(response, category.name)

        for value in BingSearchInternal().run_query(query)[0].values():
            self.assertContains(response, value)


class ShowCategoryViewTestsUsingMock(LoggedInTestCase):

    @patch('rango.views.ShowCategoryView.search.run_query', side_effect=side_effect_function)
    def test_with_side_effect_api_call(self, mock_method):
        category = CategoryFactory()
        query = " ".join(faker.words(nb=2, unique=True))
        data = {'query': query}

        response = self.client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                                    data=data)

        self.assertEquals(response.status_code, 200)

        for value in side_effect_function(query)[0].values():
            self.assertContains(response, value)

    @patch('rango.views.ShowCategoryView.search.run_query')
    def test_with_mock_api_call(self, mock_api_call):
        mock_data = [{'title': 'GitHub', 'link': 'https://github.com/', 'summary': 'Remote Code'},
                                      {'title': 'Stack Overflow', 'link': 'https://stackoverflow.com/',
                                       'summary': 'Solutions for Stupid Errors'}]

        mock_api_call.return_value = Mock()
        mock_api_call.return_value = mock_data

        category = CategoryFactory()
        query = "some query"
        data = {'query': query}

        response = self.client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                                    data=data)
        results = response.context['result_list']

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(results), 2)

        for value in mock_data[0].values():
            self.assertContains(response, value)


class AddCategoryViewTests(LoggedInTestCase):

    def test_form_display(self):
        response = self.client.get(reverse('rango:add_category'))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, ENTER_CATEGORY_MESSAGE)

    def test_form_valid(self):
        name = faker.word()
        response = self.client.post(reverse('rango:add_category'), {'name': name,
                                                                    'views': faker.random_int(min=0, max=100, step=1),
                                                                    'likes': faker.random_int(min=0, max=100, step=1),
                                                                    'slug': name})

        self.assertRedirects(response, reverse('rango:index'))

    def test_form_invalid(self):
        response = self.client.post(reverse('rango:add_category'), {})

        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(response.context['errors'])


class AddPageViewTests(LoggedInTestCase):

    def test_form_display(self):
        category = CategoryFactory()
        response = self.client.get(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, ENTER_PAGE_TITLE_MESSAGE)
        self.assertContains(response, ENTER_PAGE_URL_MESSAGE)

    def test_form_valid(self):
        category = CategoryFactory()
        response = self.client.post(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}),
                                    {'title': faker.word(),
                                     'url': faker.url(),
                                     'views': faker.random_int(min=0, max=100, step=1)})

        self.assertRedirects(response, reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))

    def test_form_invalid(self):
        category = CategoryFactory()
        response = self.client.post(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}), {})

        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(response.context['errors'])


class RestrictedViewLoggedInTest(LoggedInTestCase):

    def test_page_display(self):
        response = self.client.get(reverse('rango:restricted'))

        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'rango/restricted.html')


class RestrictedViewLoggedOutTest(LoggedOutTestCase):

    def test_page_no_display(self):
        response = self.client.get(reverse('rango:restricted'))

        self.assertRedirects(response, '/accounts/login/?next=/rango/restricted/')


class GotoUrlViewTests(TestCase):

    def test_redirects(self):
        category = CategoryFactory()
        page = PageFactory(category=category)

        response = self.client.get(reverse('rango:goto'), {'page_id': page.id})

        self.assertRedirects(response, page.url, fetch_redirect_response=False)

    def test_redirects_for_no_page(self):
        response = self.client.get(reverse('rango:goto'), {'page_id': faker.random_int(min=0, max=100, step=1)})

        self.assertRedirects(response, reverse('rango:index'))
