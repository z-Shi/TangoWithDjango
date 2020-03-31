from django.utils.decorators import method_decorator
from django.utils import timezone
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib.auth.models import User
from django.http import HttpResponse
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserProfileForm
from rango.bing_search import run_query
from datetime import datetime


class IndexView(View):
    def get(self, request):
        category_list = Category.objects.order_by('-likes')[:5]
        page_list = Page.objects.order_by('-views')[:5]

        context_dict = {'boldmessage': 'Crunchy, creamy, cookie, candy, cupcake!', 'categories': category_list,
                        'pages': page_list}

        visitor_cookie_handler(request)

        return render(request, 'rango/index.html', context=context_dict)


class AboutView(View):
    def get(self, request):
        context_dict = {}

        visitor_cookie_handler(request)
        context_dict['visits'] = request.session['visits']

        return render(request, 'rango/about.html', context=context_dict)


class ShowCategoryView(View):
    context_dict = {}
    result_list = []

    def store_data(self, category_name_slug):
        try:
            category = Category.objects.get(slug=category_name_slug)
            pages = Page.objects.filter(category=category).order_by('-views')

            self.context_dict['pages'] = pages
            self.context_dict['category'] = category
        except Category.DoesNotExist:
            self.context_dict['pages'] = None
            self.context_dict['category'] = None

    def get(self, request, category_name_slug):
        self.store_data(category_name_slug)
        self.context_dict['result_list'] = self.result_list

        return render(request, 'rango/category.html', context=self.context_dict)

    @method_decorator(login_required)
    def post(self, request, category_name_slug):
        self.store_data(category_name_slug)

        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)
            self.context_dict['query'] = query
            self.context_dict['result_list'] = result_list

        return render(request, 'rango/category.html', context=self.context_dict)


class AddCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        form = CategoryForm()
        return render(request, 'rango/add_category.html', {'form': form})

    @method_decorator(login_required)
    def post(self, request):
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return redirect(reverse('rango:index'))
        else:
            print(form.errors)

        return render(request, 'rango/add_category.html', {'form': form})


class AddPageView(View):
    category = None
    form = PageForm()
    context_dict = {}

    def load_category(self, category_name_slug):
        try:
            self.category = Category.objects.get(slug=category_name_slug)
            self.context_dict['category'] = self.category
        except Category.DoesNotExist:
            self.category = None

        if self.category is None:
            return redirect(reverse('rango:index'))

    @method_decorator(login_required)
    def get(self, request, category_name_slug):
        self.load_category(category_name_slug)
        self.context_dict['form'] = self.form

        return render(request, 'rango/add_page.html', context=self.context_dict)

    @method_decorator(login_required)
    def post(self, request, category_name_slug):
        self.load_category(category_name_slug)
        self.form = PageForm(request.POST)

        if self.form.is_valid():
            if self.category:
                page = self.form.save(commit=False)
                page.category = self.category
                page.views = 0
                page.save()

                return redirect(reverse('rango:show_category', kwargs={'category_name_slug': category_name_slug}))
        else:
            print(self.form.errors)
            self.context_dict['form'] = self.form
            return render(request, 'rango/add_page.html', context=self.context_dict)


class RestrictedView(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'rango/restricted.html')


def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', '1'))
    last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')

    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = last_visit_cookie

    request.session['visits'] = visits


class GotoUrlView(View):
    def get(self, request):
        page_id = request.GET.get('page_id')

        try:
            page = Page.objects.get(id=page_id)
        except Page.DoesNotExist:
            return redirect(reverse('rango:index'))

        page.views = page.views + 1
        page.last_visit = timezone.now()
        page.save()

        return redirect(page.url)


class RegisterProfileView(View):
    form = UserProfileForm()
    context_dict = {}

    def get(self, request):
        self.context_dict['form'] = self.form
        return render(request, 'rango/profile_registration.html', context=self.context_dict)

    def post(self, request):
        self.form = UserProfileForm(request.POST, request.FILES)

        if self.form.is_valid():
            profile = self.form.save(commit=False)
            profile.user = request.user
            profile.save()
        else:
            print(self.form.errors)

        return redirect(reverse('rango:index'))


class ProfileView(View):
    def get_user_details(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        form = UserProfileForm({'website': user_profile.website,
                                'picture': user_profile.picture})

        return user, user_profile, form

    @method_decorator(login_required)
    def get(self, request, username):
        try:
            (user, user_profile, form) = self.get_user_details(username)
        except TypeError:
            return redirect(reverse('rango:index'))

        context_dict = {'user_profile': user_profile,
                        'selected_user': user,
                        'form': form}

        return render(request, 'rango/profile.html', context_dict)

    @method_decorator(login_required)
    def post(self, request, username):
        try:
            (user, user_profile, form) = self.get_user_details(username)
        except TypeError:
            return redirect(reverse('rango:index'))

        form = UserProfileForm(request.POST, request.FILES, instance=user_profile)

        if form.is_valid():
            form.save(commit=True)
            return redirect('rango:profile', user.username)
        else:
            print(form.errors)

        context_dict = {'user_profile': user_profile,
                        'selected_user': user,
                        'form': form}

        return render(request, 'rango/profile.html', context_dict)


class ListProfilesView(View):
    @method_decorator(login_required)
    def get(self, request):
        profiles = UserProfile.objects.all()
        return render(request, 'rango/list_profiles.html', {'user_profile_list': profiles})


class LikeCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        category_id = request.GET['category_id']
        try:
            category = Category.objects.get(id=int(category_id))
        except Category.DoesNotExist:
            return HttpResponse(-1)
        except ValueError:
            return HttpResponse(-1)

        category.likes = category.likes + 1
        category.save()
        return HttpResponse(category.likes)


class CategorySuggestionView(View):
    def get(self, request):
        if 'suggestion' in request.GET:
            suggestion = request.GET['suggestion']
        else:
            suggestion = ''

        category_list = get_category_list(max_results=8, starts_with=suggestion)

        if len(category_list) == 0:
            category_list = Category.objects.order_by('-likes')

        return render(request, 'rango/categories.html', {'categories': category_list})


def get_category_list(max_results=0, starts_with=''):
    category_list = []

    if starts_with:
        category_list = Category.objects.filter(name__istartswith=starts_with)

    if max_results > 0:
        if len(category_list) > max_results:
            category_list = category_list[:max_results]

    return category_list


class SearchAddPageView(View):
    @method_decorator(login_required)
    def get(self, request):
        categoryId = request.GET['categoryId']
        title = request.GET['title']
        url = request.GET['url']

        try:
            category = Category.objects.get(id=categoryId)
        except Category.DoesNotExist:
            return HttpResponse('Category could not be found.')
        except ValueError:
            return HttpResponse('CategoryID was invalid')

        page = Page.objects.get_or_create(category=category, title=title, url=url)
        pages = Page.objects.filter(category=category).order_by('-views')

        return render(request, 'rango/list_pages.html', {'pages': pages})
