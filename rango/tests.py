from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rango.models import Category, Page


# Create your tests here.
class CategoryMethodTests(TestCase):
    def test_ensure_views_are_positive(self):
        category = add_category('test', -1)

        self.assertEqual((category.views >= 0), True)

    def test_slug_line_creation(self):
        category = add_category("Random Category String")

        self.assertEqual(category.slug, 'random-category-string')


class IndexViewTests(TestCase):
    def test_index_view_with_no_categories(self):
        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'There are no categories present.')
        self.assertQuerysetEqual(response.context['categories'], [])

    def test_index_view_with_categories(self):
        add_category('Python', 1, 1)
        add_category('C++', 1, 1)
        add_category('Erlang', 1, 1)

        response = self.client.get(reverse('rango:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python")
        self.assertContains(response, "C++")
        self.assertContains(response, "Erlang")

        num_categories = len(response.context['categories'])
        self.assertEquals(num_categories, 3)


class PageMethodTests(TestCase):
    def test_not_future_last_visit_set(self):
        category = add_category('Java', 99, 99)
        page = add_page(category, 'Ultimate Java', 'https://codewithmosh.com/p/the-ultimate-java-mastery-series')

        self.assertTrue(timezone.now() > page.last_visit)

    def test_last_visit_updated_in_goto(self):
        category = add_category('Haskell', 50, 30)
        page = add_page(category, 'Haskell for Dummies', 'https://www.snoyman.com/blog/2016/11/haskell-for-dummies')
        creation_date = page.last_visit

        self.client.get(reverse('rango:goto'), {'page_id': page.id})

        page.refresh_from_db()

        self.assertTrue(page.last_visit > creation_date)


# Helper Functions
def add_category(name, views=0, likes=0):
    category = Category.objects.get_or_create(name=name)[0]
    category.views = views
    category.likes = likes
    category.save()
    return category


def add_page(category, title, url):
    return Page.objects.get_or_create(category=category, title=title, url=url)[0]
