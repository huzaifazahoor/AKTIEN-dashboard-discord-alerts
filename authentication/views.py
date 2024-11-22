from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import CustomUserCreationForm
from .models import CustomUser
from .tokens import email_verification_token


class CustomLoginView(LoginView):
    template_name = "authentication/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(
                "public_dashboard"
            )  # Redirect to dashboard if already logged in
        return super().dispatch(request, *args, **kwargs)


def signup(request):
    if request.user.is_authenticated:
        return redirect("public_dashboard")
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verify = False
            user.save()

            # Generate token and UID
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = email_verification_token.make_token(user)

            # Send verification email
            verification_link = request.build_absolute_uri(
                reverse("verify_email", args=[uid, token])
            )
            send_mail(
                "Verify your email address",
                f"Please click this link to verify your email: {verification_link}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            messages.success(
                request,
                (
                    "Please check your email to verify your account. "
                    "This helps ensure accurate salary data and improves your experience on SalaryScout. "
                ),
            )
            return redirect("login")
    else:
        form = CustomUserCreationForm()
    return render(request, "authentication/signup.html", {"form": form})


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_verify = True
        user.save()
        login(request, user)
        messages.success(request, "Your email has been verified. Welcome!")
        return redirect("public_dashboard")
    else:
        messages.error(request, "The verification link was invalid or has expired.")
        return redirect("login")


@login_required
def resend_verification_email(request):
    user = request.user

    if not user.is_verify:
        # Send the verification email
        # Generate token and UID
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        # Send verification email
        verification_link = request.build_absolute_uri(
            reverse("verify_email", args=[uid, token])
        )
        subject = "Verify your email address"
        message = f"Please click this link to verify your email: {verification_link}"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [request.user.email]

        send_mail(
            subject,
            message,
            from_email,
            recipient_list,
            fail_silently=False,
        )

        # Add success message
        messages.success(
            request, "Verification email has been resent. Please check your inbox."
        )
    else:
        # Add info message if already verified
        messages.info(request, "Your account is already verified.")

    return redirect("public_dashboard")
