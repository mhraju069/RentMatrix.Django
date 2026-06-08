import asyncio
import stripe
from django.conf import settings
from .models import Payment

stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "sk_test_placeholder_key")


async def Create_payment_intent(request, booking_id, amount, payment_method_id):
    payment = await Payment.objects.acreate(
        booking_id=booking_id,
        amount=amount,
        status='pending'
    )

    try:
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=int(float(amount) * 100),
            currency='usd',
            payment_method=payment_method_id,
            confirm=True,
            off_session=True,
            metadata={
                "payment": str(payment.id),
                "booking": str(booking_id),
                "user": request.user.email
            },
            return_url=request.build_absolute_uri('/api/v1/booking/payment/success')
        )

        if intent.status == 'succeeded':
            payment.status = 'succeeded'
            payment.payment_intent_id = intent.id
            if hasattr(intent, 'charges') and intent.charges.data:
                payment.tnxid = intent.charges.data[0].id
                payment.invoice = intent.charges.data[0].receipt_url
                
            await payment.asave()
            return {
                "status": 200,
                "success": True,
                "payment_id": str(payment.id),
                "client_secret": intent.client_secret,
                "invoice_url": payment.invoice
            }
        elif intent.status in ('requires_action', 'requires_source_action'):
            payment.status = 'requires_action'
            payment.payment_intent_id = intent.id
            payment.tnxid = None
            await payment.asave()
            return {
                "status": 200,
                "success": True,
                "client_secret": intent.client_secret,
                "requires_action": True
            }
        else:
            payment.status = 'failed'
            await payment.asave()
            return {
                "status": 500,
                "success": False,
                "message": f"Payment intent status: {intent.status}"
            }

    except stripe.error.CardError as e:
        payment.status = 'failed'
        await payment.asave()
        return {
            "status": 400,
            "success": False,
            "message": f"Card Error: {e.user_message if hasattr(e, 'user_message') else str(e)}",
        }
        
    except Exception as e:
        payment.status = 'failed'
        await payment.asave()
        return {
            "status": 500,
            "success": False,
            "message": f"Error: {str(e)}",
        }


async def Refund_payment(payment_intent_id):
    try:
        refund = await asyncio.to_thread(
            stripe.Refund.create,
            payment_intent=payment_intent_id
        )
        if refund.status in ('succeeded', 'pending'):
            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status
            }
        else:
            return {
                "success": False,
                "message": f"Refund status: {refund.status}"
            }
    except stripe.error.StripeError as e:
        return {
            "success": False,
            "message": f"Stripe Error: {e.user_message if hasattr(e, 'user_message') else str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }