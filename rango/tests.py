from unittest.mock import patch, Mock

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User

from rango.bing_search import BingSearchExternal
from rango.models import Category, Page


# Login TestCase
class LoginTestCase(TestCase):

    def setUp(self):
        user = User.objects.create(username='test')
        user.set_password('super_str0ng!')
        user.save()

        self.client.login(username='test', password='super_str0ng!')


class LoggedOutTestCase(TestCase):
    pass  # simply to have a logged out test case to differentiate and inherit TestCase as expected


# Test Cases
class CategoryTests(LoggedOutTestCase):

    def test_views_positive(self):
        category = add_category("test", -1)

        self.assertTrue(category.views >= 0)

    def test_slug_creation(self):
        category = add_category("Brilliant Work")

        self.assertEqual(category.slug, "brilliant-work")


class PageTests(LoggedOutTestCase):

    def test_last_visit(self):
        category = add_category('Java', 99, 99)
        page = add_page(category, 'Ultimate Java', 'https://codewithmosh.com/p/the-ultimate-java-mastery-series')

        self.assertTrue(timezone.now() >= page.last_visit)

    def test_last_visit_updated_by_goto(self):
        category = add_category('Haskell', 50, 30)
        page = add_page(category, 'Haskell for Dummies', 'https://www.snoyman.com/blog/2016/11/haskell-for-dummies')
        creation_date = page.last_visit

        self.client.get(reverse('rango:goto'), {'page_id': page.id})

        page.refresh_from_db()

        self.assertTrue(page.last_visit > creation_date)


class IndexViewTests(LoggedOutTestCase):

    def test_no_categories_or_pages(self):
        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'There are no categories present.')
        self.assertQuerysetEqual(response.context['categories'], [])
        self.assertContains(response, 'There are no pages present.')
        self.assertQuerysetEqual(response.context['pages'], [])

    def test_categories_no_pages(self):
        add_category('Python', 1, 1)
        add_category('C++', 1, 1)
        add_category('Erlang', 1, 1)

        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python')
        self.assertContains(response, 'C++')
        self.assertContains(response, 'Erlang')

        categories = len(response.context['categories'])
        self.assertEqual(categories, 3)

    def test_pages_and_categories(self):
        shield = add_category('SHIELD', 99, 99)
        hydra = add_category('HYDRA', 50, 50)

        add_page(shield, 'Quake', 'https://marvelcinematicuniverse.fandom.com/wiki/Quake')
        add_page(hydra, 'Ward', 'https://marvelcinematicuniverse.fandom.com/wiki/Grant_Ward')

        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'SHIELD')
        self.assertContains(response, 'HYDRA')

        categories = len(response.context['categories'])
        self.assertEqual(categories, 2)

        self.assertContains(response, 'Quake')
        self.assertContains(response, 'Ward')

        pages = len(response.context['pages'])
        self.assertEqual(pages, 2)


class AboutViewTests(LoggedOutTestCase):

    def test_visited(self):
        response = self.client.get(reverse('rango:about'))

        visits = response.context['visits']

        self.assertEquals(visits, 1)


class ShowCategoryViewTestsUsingStub(LoggedOutTestCase):

    def test_category_no_pages(self):
        category = add_category("Random Category", 0, 0)

        response = self.client.get(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Random Category')
        self.assertContains(response, 'There are no pages present.')
        self.assertQuerysetEqual(response.context['pages'], [])
        self.assertQuerysetEqual(response.context['result_list'], [])

    def test_category_with_pages(self):
        category = add_category("Another Category", 0, 0)
        add_page(category, 'Some Page', 'https://www.google.co.uk')

        response = self.client.get(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))
        pages = len(response.context['pages'])

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Another Category')
        self.assertContains(response, 'Some Page')
        self.assertEquals(pages, 1)
        self.assertQuerysetEqual(response.context['result_list'], [])

    def test_category_not_logged_in(self):
        category = add_category("Another Category", 0, 0)
        query = "cookies"

        response = self.client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                                    data={'query': query})

        self.assertRedirects(response, '/accounts/login/?next=/rango/category/another-category/')

    def test_with_stubbed_api_call(self):
        category = add_category("Another Category", 0, 0)
        query = "some query"
        data = {'query': query, 'internal': True}

        user = User.objects.create(username='test')
        user.set_password('super_str0ng!')
        user.save()

        client = Client()
        client.login(username='test', password='super_str0ng!')

        response = client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                               data=data)
        results = response.context['result_list']

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(results), 1)
        self.assertContains(response, 'Another Category')
        self.assertContains(response, 'https://www.bbcgoodfood.com/recipes/collection/cookie')
        self.assertContains(response, 'Cookies')


class ShowCategoryViewTestsUsingMock(LoginTestCase):

    @patch('rango.views.ShowCategoryView.search.run_query')
    def test_with_mock_api_call(self, mock_api_call):
        mock_api_call.return_value = Mock()
        mock_api_call.return_value = [{'title': 'GitHub', 'link': 'https://github.com/', 'summary': 'Remote Code'},
                                      {'title': 'Stack Overflow', 'link': 'https://stackoverflow.com/',
                                       'summary': 'Solutions for Stupid Errors'}]

        category = add_category("Another Category", 0, 0)
        query = "some query"
        data = {'query': query}

        response = self.client.post(reverse('rango:show_category', kwargs={'category_name_slug': category.slug}),
                                    data=data)
        results = response.context['result_list']

        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(results), 2)
        self.assertContains(response, 'https://github.com/')
        self.assertContains(response, 'https://stackoverflow.com/')


class AddCategoryViewTests(LoginTestCase):

    def test_form_display(self):
        response = self.client.get(reverse('rango:add_category'))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'enter the category name')

    def test_form_valid(self):
        response = self.client.post(reverse('rango:add_category'), {'name': 'random', 'views': 100, 'likes': 10,
                                                                    'slug': 'random'})

        self.assertRedirects(response, reverse('rango:index'))

    def test_form_invalid(self):
        response = self.client.post(reverse('rango:add_category'), {})

        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(response.context['errors'])


class AddPageViewTests(LoginTestCase):

    def test_form_display(self):
        category = add_category('Random Category', 0, 0)
        response = self.client.get(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}))

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'enter the title of the page')
        self.assertContains(response, 'enter the URL of the page')

    def test_form_valid(self):
        category = add_category('Random Category', 0, 0)
        response = self.client.post(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}),
                                    {'title': 'Random Page', 'url': 'https://www.google.co.uk', 'views': 0})

        self.assertRedirects(response, reverse('rango:show_category', kwargs={'category_name_slug': category.slug}))

    def test_form_invalid(self):
        category = add_category('Random Category', 0, 0)
        response = self.client.post(reverse('rango:add_page', kwargs={'category_name_slug': category.slug}), {})

        self.assertEquals(response.status_code, 200)
        self.assertIsNotNone(response.context['errors'])


class RestrictedViewLoggedInTest(LoginTestCase):

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
        url = 'https://www.google.co.uk'
        category = add_category('Random Category', 0, 0)
        page = add_page(category, 'Random Page', url)

        response = self.client.get(reverse('rango:goto'), {'page_id': page.id})

        self.assertRedirects(response, url, fetch_redirect_response=False)


# Helper Functions
def add_category(name, views=0, likes=0):
    category = Category.objects.get_or_create(name=name)[0]
    category.views = views
    category.likes = likes
    category.save()

    return category


def add_page(category, title, url):
    return Page.objects.get_or_create(category=category, title=title, url=url)[0]
