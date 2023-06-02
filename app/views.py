import decimal
from django.shortcuts import render, HttpResponseRedirect, get_object_or_404, redirect
from .forms import*
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import *
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator # for Class Based Views
from django.views import View
import requests
from django.urls import reverse


# Create your views here.

def index(request):
    return render(request, 'app/index.html')

def category(request):
    cat = Category.objects.all()
    return render(request, 'app/category.html',  {'category':cat})


def productdetail(request, pk):
    product = Product.objects.filter(id=pk)
    
    return render(request, 'app/productdetail.html',  {'product':product})


@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        form = AddressForm()
        return render(request, 'app/add_address.html', {'form': form})

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            user=request.user
            address = form.cleaned_data['address']
            reg = Address(user=user, address=address)
            reg.save()
            messages.success(request, "New Address Added Successfully.")
        return redirect('profile')

@login_required
def remove_address(request, id):
    a = get_object_or_404(Address, user=request.user, id=id)
    a.delete()
    messages.success(request, "Address removed.")
    return redirect('profile')



@login_required
def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('prod_id')
    product = get_object_or_404(Product, id=product_id)

    # Check whether the Product is alread in Cart or Not
    item_already_in_cart = Cart.objects.filter(product=product_id, user=user)
    if item_already_in_cart:
        cp = get_object_or_404(Cart, product=product_id, user=user)
        cp.quantity += 1
        cp.save()
    else:
        Cart(user=user, product=product).save()

    return redirect('cart')

@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)
    cp = [p for p in Cart.objects.all() if p.user==user]
    amount = decimal.Decimal(0)
    total_amount=0
    shipping = 100
    if cp:
        for p in cp:
            temp_amount = (p.quantity*p.product.price)
            amount += temp_amount
            
            total_amount = amount + shipping

    if request.method == 'POST':
        fm = CheckoutForm(request.POST)
        user = request.user
        if fm.is_valid():
            cart = Cart.objects.filter(user=user)
            address = fm.cleaned_data['address']
            mobile = fm.cleaned_data['mobile']
            email = fm.cleaned_data['email']            
            pm = fm.cleaned_data['payment_method']
            for c in cart:
                corder = Ordered(user=c.user, product=c.product, address=address,mobile=mobile, email=email,quantity= c.quantity, total=total_amount, payment_method=pm)
                corder.save()
                if pm == 'Esewa':
                    c.delete()
                    return redirect(reverse("esewarequest") + "?o_id=" + str(corder.id))
                    
                # And Deleting from Cart
                c.delete()
            return redirect('cart')

    else:
        fm = CheckoutForm()

    context = {
        'cart_products': cart_products,
        'amount':amount,
        'total_amount':total_amount ,
        'shipping':shipping,
        'form':fm

       }

    return render(request, 'app/cart_checkout.html', context)


@login_required
def remove_cart(request, cart_id):
    if request.method == 'GET':
        c = get_object_or_404(Cart, id=cart_id)
        c.delete()
        
    return redirect('cart')


@login_required
def plus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        cp.quantity += 1
        cp.save()
    return redirect('cart')


@login_required
def minus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        # Remove the Product if the quantity is already 1
        if cp.quantity == 1:
            cp.delete()
        else:
            cp.quantity -= 1
            cp.save()
    return redirect('cart')

@login_required
def checkout(request):
    user = request.user
    address_id = request.get('address')
    address = get_object_or_404(Address, id=address_id)    
    payment = request.get('payment')
    
    # Get all the products of User in Cart
    cart = Cart.objects.filter(user=user)
    for c in cart:
        # Saving all the products from Cart to Order
        Order(user=user, address=address, product=c.product, quantity=c.quantity,payment_method=payment).save()
        c.delete()
        if payment == 'e-Sewa':
            
            return render(request, "app/esewarequest.html" + "?o_id=" + str(Order.id))
     
        # And Deleting from Cart
        
    return redirect('cart')


class EsewaRequestView(View):
    def get(self, request, *args, **kwargs):
        o_id = request.GET.get("o_id")
        order = Ordered.objects.get(id=o_id)
        context = {
            "order": order
        }
        return render(request, "app/esewarequest.html", context)

class EsewaVerifyView(View):
    def get(self, request, *args, **kwargs):
        import xml.etree.ElementTree as ET
        oid = request.GET.get("oid")
        amt = request.GET.get("amt")
        refId = request.GET.get("refId")

        url = "https://uat.esewa.com.np/epay/transrec"
        d = {
            'amt': amt,
            'scd': 'epay_payment',
            'rid': refId,
            'pid': oid,
        }
        resp = requests.post(url, d)
        root = ET.fromstring(resp.content)
        status = root[0].text.strip()

        order_id = oid.split("_")[1]
        order_obj = Ordered.objects.get(id=order_id)
        if status == "Success":
            order_obj.payment_completed = True
            order_obj.save()

            return redirect("cart")
        else:

            return redirect("/esewa-request/?o_id="+order_id)

@login_required
def orders(request):
    all_orders = Ordered.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'app/orders.html', {'orders': all_orders})


def base(request):
    return render(request, 'app/base.html')

def register(request):

    if request.method == 'POST':
        fm = CustomerRegistrationForm(request.POST)
        if fm.is_valid():
            fm.save()
            fm = CustomerRegistrationForm()

    else:
        fm = CustomerRegistrationForm()
    

    return render(request, 'app/register.html', {'form':fm})

def user_login(request):
    if request.method == 'POST':
        fm = AuthenticationForm(data=request.POST)
        if fm.is_valid():
            user = fm.get_user()
            login(request, user)
            return HttpResponseRedirect('/profile/')

    else:
        fm = AuthenticationForm()
    return render(request, 'app/user_login.html',{'form':fm})




def user_profile(request):
    if request.user.is_authenticated:
        address = Address.objects.all()
        #address = Address.objects.filter(user=request.user)

        return render(request, 'app/profile.html', {'name': request.user, 'address':address})
    else:
        return HttpResponseRedirect('/login/')


def user_logout(request):
    logout (request)
    return HttpResponseRedirect('/accounts/login/')

