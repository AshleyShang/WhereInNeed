from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Count
from django.http import Http404
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse
from django.db import connection


from .models import Charity, Categ
from .forms import *



def home(request):
    #charities = Charity.objects.all()
    charity_list = Charity.objects.all()
    paginator = Paginator(charity_list, 10) # Show 25 records per page
    # paginator = Paginator(contact_list, 25,5) #limit min records per page
    page = request.GET.get('page')
    try:
        charities = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        charities = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        charities = paginator.page(paginator.num_pages)
    return render(request, 'home.html', {'charities': charities})

def charity_detail(request, id):
    try:
        charity = Charity.objects.get(id = id)
        is_liked = False
        if charity.likes.filter(id = request.user.id).exists():
            is_liked = True
        categoryset = []
        returnlist = []
        for cat in charity.category.all():
            categoryset.append(cat.name)
        for catename in categoryset:
            charityset = Charity.objects.filter(category__name=catename).annotate(total_votes=Count('likes')).order_by('-total_votes')[:3]
            for item in charityset:
                returnlist.append(item)
    except Charity.DoesNotExist:
        raise Http404('Charity not found')
    return render(request, 'charity_detail.html', {'charity': charity, 'is_liked': is_liked, 'total_likes':charity.total_likes(),'recommendlist':returnlist})

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})




def logout_request(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect("/")


def login_request(request):
    if request.method == 'POST':
        form = AuthenticationForm(request=request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"You are now logged in as {username}")
                return redirect('/')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    form = AuthenticationForm()
    return render(request = request,
                    template_name = "login.html",
                    context={"form":form})


def searchposts(request):
    charities_list = Charity.objects.all()
    query= request.GET.get('q')

    submitbutton= request.GET.get('submit')

    if query:
        charities_list= Charity.objects.raw("""
        SELECT DISTINCT *
        FROM myapp_charity c JOIN myapp_charity_category x ON c.id = x.charity_id
            JOIN myapp_categ categ ON x.categ_id = categ.id
        WHERE c.city LIKE %s or c.name LIKE %s or categ.name LIKE %s
        ORDER BY c.rating DESC
        """, params=['%'+query+'%', '%'+query+'%', '%'+query+'%'])
        #lookups= Q(name__icontains=query) | Q(city__icontains=query) |  Q(category__name__icontains=query)

        #charities_list= Charity.objects.filter(lookups).distinct()

        result= Charity.objects.raw("""
        SELECT *, count(*) as num
        FROM myapp_charity c JOIN myapp_charity_category x ON c.id = x.charity_id
            JOIN myapp_categ categ ON x.categ_id = categ.id
        WHERE c.city LIKE %s or c.name LIKE %s or categ.name LIKE %s
        GROUP BY c.rating
        ORDER BY c.rating DESC
        """, params=['%'+query+'%', '%'+query+'%', '%'+query+'%'])

        paginator = Paginator(charities_list, 10) # 10 posts per page
        page = request.GET.get('page')

        try:
            charities = paginator.page(page)
        except PageNotAnInteger:
            charities = paginator.page(1)
        except EmptyPage:
            charities = paginator.page(paginator.num_pages)

        return render(request, 'search.html', {'charities': charities, 'result': result})

    else:
        return render(request, 'search.html')



def like(request):
    #charity = get_object_or_404(Charity, id = request.POST.get('charity_id'))
    try:
        charity = Charity.objects.get(id = request.POST.get('charity_id'))        
        if charity.likes.filter(id = request.user.id).exists():
            #charity.likes.remove(request.user)
            with connection.cursor() as cursor:
                cursor.execute('''
                DELETE FROM myapp_charity_likes
                WHERE user_id = %s AND charity_id = %s ''' ,
                [request.user.id, charity.id]
                )
            is_liked = False
        else:
            #charity.likes.add(request.user)
            with connection.cursor() as cursor:
                cursor.execute('''
                INSERT INTO myapp_charity_likes(charity_id,user_id) VALUES( %s , %s )''',
                [charity.id, request.user.id])
            is_liked = True
        return HttpResponseRedirect(charity.get_absolute_url())

    except:
        return render(request, 'error.html')


@login_required
def update_profile(request):
    args = {}

    if request.method == 'POST':
        user_form = UpdateProfile(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            bio = profile_form.cleaned_data['bio']
            city = profile_form.cleaned_data['city']
            with connection.cursor() as cursor:
                cursor.execute('''
                UPDATE myapp_profile SET bio = %s, city = %s WHERE id = %s''',
                [bio, city, request.POST.get('id')])
        
            user_form.save()
            #profile_form.save()
            return HttpResponseRedirect(
               reverse(user_profile, 
                       args=[request.user.username]))
    else:
        user_form = UpdateProfile(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
    return render(request, 'update_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })
        #form = UpdateProfile(request.POST, instance=request.user)
        #form.actual_user = request.user
        #if form.is_valid():
            #form.save()
            #return HttpResponseRedirect(
               #reverse(user_profile, 
                       #args=[request.user.username]))
    #else:
        #form = UpdateProfile()

    #args['form'] = form
    #return render(request, 'update_profile.html', args)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Your password was successfully updated!')
            return redirect('/')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {
        'form': form
    })


@login_required
def delete_profile(request,username):
    context = {}
    user = User.objects.get(username=username)
    #user = User.objects.filter(id = request.user.profile.user_id)
    try:
        user.delete()
        context['msg'] = 'The user is deleted.'
    except User.DoesNotExist:
        context['msg'] = 'User does not exist.'
    except Exception as e:
        context['msg'] = e.message

    return render(request, 'delete_profile.html', context=context)

@login_required
def user_profile(request, username):
    user = User.objects.get(username=username)
    charityset = Charity.objects.filter(likes=user)
    return_list = []
    for item in charityset:
        return_list.append(item)
    return render(request, 'user_profile.html',{ "user":user,'likelist': return_list})

def category_view(request,*args,**kwargs):
    charities=Charity.objects.all()
    categs= Categ.objects.all()
    categories=[]
    for category in categs:
        if category not in categories:
            categories.append(category)
    return render(request,'category.html',{'charities': charities,'categories':categories,'categs':categs})

def rating_view(request,*args,**kwargs):
    charities=Charity.objects.all()
    ratings=[4,3,2,1]
    return render(request,'rating.html',{'charities':charities,'ratings':ratings})

def city_view(request,*args,**kwargs):
    charities=Charity.objects.all()
    cities=[]
    for charity in charities:
        if charity.city not in cities:
            cities.append(charity.city)
    return render(request,'city.html',{'charities':charities,'cities':cities})
