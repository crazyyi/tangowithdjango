from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from rango.models import Category
from rango.models import Page
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm, LoginForm
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib import messages
from django.contrib.messages import get_messages
from datetime import datetime

def index(request):
	#Request the context of the request.
	#The context contains infromation such as the client's machine details, for example.
	context = RequestContext(request)

	# Construct a dictionary to pass to the tempalte engine as its context.
	# Note the key boldmessage is the same as {{ boldmessage }} in the tempalte!
	category_list = Category.objects.all()
	
	context_dict = {'categories':category_list}

	cat_list = get_category_list()
	context_dict['cat_list'] = cat_list

	# The following two lines are new.
	# We loop through each category returned, and create a URL attribute.
	# This attribute stores an encoded URL
	for category in category_list:
		category.url = encode_url(category.name)

	page_list = Page.objects.order_by('-views')[:5]
	context_dict['pages'] = page_list

	if request.session.get('last_visit'):
		last_visit_time = request.session.get('last_visit')
		print "Last visit: ", last_visit_time
		visits = request.session.get('visits', 0)
		print "Total visits: ", visits

		if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).seconds > 5:
			request.session['visits'] = visits + 1
			request.session['last_visit'] = str(datetime.now())

	else:
		request.session['last_visit'] = str(datetime.now())
		request.session['visits'] = 1

	return render_to_response('rango/index.html', context_dict, context)

def about(request):
	context = RequestContext(request)

	if request.session.get('visits'):
		count = request.session.get('visits')
	else:
		count = 0

	return render_to_response('rango/about.html', {'visits': count}, context)

def category(request, category_name_url):
	context = RequestContext(request)

	category_name = decode_url(category_name_url)

	cat_list = get_category_list()

	# Create a context dictionary which we can pass to the template rendering engine.
	# We start by containing the name of the category passed by the user.
	context_dict = {'category_name': category_name}
	context_dict['cat_list'] = cat_list

	try:
		# Can we find a category with the given name?
	# If we can't, the .get() method raises a DoesNotExist exception.
	# So the .get() method returns one model instance or raises an exception.
		category = Category.objects.get(name=category_name)

	# Retrieve all of the associate pages.
	# Note that filter returns >= 1 model instance.
		pages = Page.objects.filter(category=category)

	# Adds our results list to the template context under name pages.
		context_dict['pages'] = pages
		# We also add the category object from the database to the context dictionary.
	# We'll use this in the template to verify that the category exists.
		context_dict['category'] = category
		context_dict['category_name_url'] = category_name_url

	except Category.DoesNotExist:
	# We get here if we didn't find the specified category.
	# Don't do anything - the template displays the "no category" message for us.
		pass

	# Go render the response and return it to the client.
	return render_to_response('rango/category.html', context_dict, context)

@login_required
def add_category(request):
	# Get the context from the request.
	context = RequestContext(request)

	# A HTTP POST?
	if request.method == 'POST':
		form = CategoryForm(request.POST)

		# Have we been provided with valid form?
		if form.is_valid():
			# Save the new provided with a valid form?
			form.save(commit=True)
	 
			# New call the index() view
			# The user will be shown the homepage.
			return index(request)
		else:
			# The supplied form contained errors - jsut print them to the terminal.
			print form.errors
	else:
	# The supplied form contained errors - just print them to the terminal.
		form = CategoryForm()

	return render_to_response('rango/add_category.html', {'form':form}, context)

@login_required
def add_page(request, category_name_url):
	context = RequestContext(request)

	category_name = decode_url(category_name_url)

	cat_list = get_category_list()

	if request.method == 'POST':
		form = PageForm(request.POST)

		if form.is_valid():
	
	   		page = form.save(commit = False)

			try:
				cat = Category.objects.get(name=category_name)
				page.category = cat
			except Category.DoesNotExist:
				return render_to_response('rango/add_category.html', {}, context)
		
			page.views = 0

			page.save()

			return category(request, category_name_url)
		else:
			print form.errors
	else:
		form = PageForm()

	return render_to_response('rango/add_page.html',
		{'category_name_url': category_name_url,
		 'category_name': category_name,
		 'cat_list': cat_list,
		 'form': form}, context)

def register(request):
	if request.session.test_cookie_worked():
		print ">>>> TEST COOKIE WORKED!"
		request.session.delete_test_cookie()

	context = RequestContext(request)
	registered = False

	# If it's a HTTP POST, we're interested in procssing form data.
	if request.method == 'POST':
		user_form = UserForm(data=request.POST)
		profile_form = UserProfileForm(data=request.POST)

		if user_form.is_valid() and profile_form.is_valid():
			user = user_form.save()

			user.set_password(user.password)
			user.save()

			profile = profile_form.save(commit=False)
			profile.user = user

			if 'picture' in request.FILES:
				profile.picture = request.FILES['picture']

			profile.save()

			registered = True

		else:
			print user_form.errors, profile_form.errors

	else:
		user_form = UserForm()
		profile_form = UserProfileForm()

	return render_to_response(
			'rango/register.html',
			{'user_form': user_form, 'profile_form': profile_form, 'registered': registered},
			context
			)

def user_login(request):
	context = RequestContext(request)

	if request.method == 'POST':
		login_form = LoginForm(data=request.POST)
		username = request.POST['username']
		password = request.POST['password']

		user = authenticate(username=username, password=password)

		if user is not None:
			if user.is_active:
				login(request, user)
				return HttpResponseRedirect('/rango/')
			else:
				return HttpResponse("Your Rango account is disabled.")

		else:
			messages.warning(request, 'Invalid login details supplied.')
			#print "Invalid login details: {0}, {1}".format(username, password)
			#return HttpResponse("Invalid login details supplied.")
			login_form = LoginForm()

			context_dict = {'login_form': login_form}
			context_dict['warning'] = get_messages(request)
			return render_to_response('rango/login.html', context_dict, context)

	else:
		login_form = LoginForm()
		return render_to_response('rango/login.html', {'login_form':login_form}, context)

@login_required
def restricted(request):
	return HttpResponse("Since you're logged in, you can see this text.")

@login_required
def user_logout(request):
	logout(request)

	return HttpResponseRedirect('/rango/')

def get_category_list():
    cat_list = Category.objects.all()

    for cat in cat_list:
        cat.url = encode_url(cat.name)

    return cat_list

def decode_url(category_name_url):
	return category_name_url.replace('_', ' ')

def encode_url(category_name):
	return category_name.replace(' ', '_')
	
