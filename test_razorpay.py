import razorpay
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')

print(f"Key ID: {RAZORPAY_KEY_ID}")

try:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    
    order_data = {
        'amount': 500 * 100, # 500 INR
        'currency': 'INR',
        'payment_capture': '1'
    }
    print("Creating order...")
    # Try both ways if needed, but let's try the one in the code first
    razorpay_order = client.order.create(data=order_data)
    print("Order Created Successfully!")
    print(razorpay_order)
except Exception as e:
    print(f"Order Creation Failed: {e}")
    # Try without 'data=' kwarg
    try:
        print("Retrying without 'data=' keyword...")
        razorpay_order = client.order.create(order_data)
        print("Order Created Successfully (without data=)!")
        print(razorpay_order)
    except Exception as e2:
         print(f"Order Creation Failed again: {e2}")
