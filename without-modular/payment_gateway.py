#!/usr/bin/env python3
"""
Payment Gateway Integration
Supports Stripe, Razorpay, and PayPal for online payments
"""

import stripe
import razorpay
import paypalrestsdk
import json
import logging
from datetime import datetime, timedelta
from flask import current_app, request, jsonify
from flask_login import current_user
import hashlib
import hmac
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentGateway:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_payment_tables()
        
        # Load configuration
        self.config = app.config.get('PAYMENT_CONFIG', {})
        
        # Initialize payment gateways
        self._init_stripe()
        self._init_razorpay()
        self._init_paypal()
    
    def setup_payment_tables(self):
        """Create payment-related tables"""
        
        class PaymentTransaction(self.db.Model):
            __tablename__ = 'payment_transactions'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            transaction_id = self.db.Column(self.db.String(100), unique=True, nullable=False)
            bill_id = self.db.Column(self.db.Integer, self.db.ForeignKey('bill.id'), nullable=False)
            patient_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_patient.id'), nullable=False)
            
            # Payment details
            gateway = self.db.Column(self.db.String(20), nullable=False)  # stripe, razorpay, paypal
            gateway_transaction_id = self.db.Column(self.db.String(100))
            amount = self.db.Column(self.db.Float, nullable=False)
            currency = self.db.Column(self.db.String(3), default='USD')
            
            # Status tracking
            status = self.db.Column(self.db.String(20), default='pending')  # pending, processing, completed, failed, refunded
            payment_method = self.db.Column(self.db.String(50))  # card, upi, netbanking, wallet
            
            # Gateway response
            gateway_response = self.db.Column(self.db.Text)  # JSON response from gateway
            failure_reason = self.db.Column(self.db.String(200))
            
            # Timestamps
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            completed_at = self.db.Column(self.db.DateTime)
            
            # Relationships
            bill = self.db.relationship('Bill', backref='payment_transactions')
            patient = self.db.relationship('WebPatient', backref='payment_transactions')
        
        class PaymentRefund(self.db.Model):
            __tablename__ = 'payment_refunds'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            refund_id = self.db.Column(self.db.String(100), unique=True, nullable=False)
            transaction_id = self.db.Column(self.db.Integer, self.db.ForeignKey('payment_transactions.id'), nullable=False)
            
            # Refund details
            amount = self.db.Column(self.db.Float, nullable=False)
            reason = self.db.Column(self.db.String(200))
            gateway_refund_id = self.db.Column(self.db.String(100))
            
            # Status
            status = self.db.Column(self.db.String(20), default='pending')  # pending, completed, failed
            
            # Audit
            requested_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            completed_at = self.db.Column(self.db.DateTime)
            
            # Relationships
            transaction = self.db.relationship('PaymentTransaction', backref='refunds')
            requester = self.db.relationship('WebUser', backref='requested_refunds')
        
        # Store model classes
        self.PaymentTransaction = PaymentTransaction
        self.PaymentRefund = PaymentRefund
        
        # Create tables
        self.db.create_all()
    
    def _init_stripe(self):
        """Initialize Stripe"""
        try:
            stripe_config = self.config.get('stripe', {})
            if stripe_config.get('secret_key'):
                stripe.api_key = stripe_config['secret_key']
                self.stripe_enabled = True
                logger.info("Stripe payment gateway initialized")
            else:
                self.stripe_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Stripe: {str(e)}")
            self.stripe_enabled = False    
    def _init_razorpay(self):
        """Initialize Razorpay"""
        try:
            razorpay_config = self.config.get('razorpay', {})
            if razorpay_config.get('key_id') and razorpay_config.get('key_secret'):
                self.razorpay_client = razorpay.Client(
                    auth=(razorpay_config['key_id'], razorpay_config['key_secret'])
                )
                self.razorpay_enabled = True
                logger.info("Razorpay payment gateway initialized")
            else:
                self.razorpay_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Razorpay: {str(e)}")
            self.razorpay_enabled = False
    
    def _init_paypal(self):
        """Initialize PayPal"""
        try:
            paypal_config = self.config.get('paypal', {})
            if paypal_config.get('client_id') and paypal_config.get('client_secret'):
                paypalrestsdk.configure({
                    "mode": paypal_config.get('mode', 'sandbox'),
                    "client_id": paypal_config['client_id'],
                    "client_secret": paypal_config['client_secret']
                })
                self.paypal_enabled = True
                logger.info("PayPal payment gateway initialized")
            else:
                self.paypal_enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize PayPal: {str(e)}")
            self.paypal_enabled = False
    
    # ==================== STRIPE INTEGRATION ====================
    
    def create_stripe_payment_intent(self, bill_id, amount, currency='usd'):
        """Create Stripe payment intent"""
        try:
            if not self.stripe_enabled:
                raise ValueError("Stripe is not configured")
            
            from web_app import Bill
            bill = db.session.get(Bill, bill_id)
            if not bill:
                raise ValueError("Bill not found")
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Stripe uses cents
                currency=currency,
                metadata={
                    'bill_id': str(bill_id),
                    'patient_id': str(bill.patient_id),
                    'hospital': 'MediCare Pro'
                }
            )
            
            # Create transaction record
            transaction = self.PaymentTransaction(
                transaction_id=self._generate_transaction_id(),
                bill_id=bill_id,
                patient_id=bill.patient_id,
                gateway='stripe',
                gateway_transaction_id=intent.id,
                amount=amount,
                currency=currency.upper(),
                status='pending'
            )
            
            self.db.session.add(transaction)
            self.db.session.commit()
            
            return {
                'client_secret': intent.client_secret,
                'transaction_id': transaction.transaction_id,
                'amount': amount,
                'currency': currency
            }
            
        except Exception as e:
            logger.error(f"Failed to create Stripe payment intent: {str(e)}")
            raise
    
    def confirm_stripe_payment(self, payment_intent_id):
        """Confirm Stripe payment"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            transaction = self.PaymentTransaction.query.filter_by(
                gateway_transaction_id=payment_intent_id
            ).first()
            
            if not transaction:
                raise ValueError("Transaction not found")
            
            if intent.status == 'succeeded':
                transaction.status = 'completed'
                transaction.completed_at = datetime.utcnow()
                transaction.payment_method = intent.charges.data[0].payment_method_details.type if intent.charges.data else 'card'
                
                # Update bill payment status
                from web_app import Bill, Payment
                bill = Bill.query.get(transaction.bill_id)
                if bill:
                    # Create payment record
                    payment = Payment(
                        bill_id=bill.id,
                        amount=transaction.amount,
                        payment_method='online',
                        transaction_id=payment_intent_id,
                        received_by=current_user.id if current_user.is_authenticated else None
                    )
                    
                    self.db.session.add(payment)
                    
                    # Update bill amounts
                    bill.paid_amount += transaction.amount
                    bill.balance_amount = bill.total_amount - bill.paid_amount
                    
                    if bill.balance_amount <= 0:
                        bill.payment_status = 'paid'
                    elif bill.paid_amount > 0:
                        bill.payment_status = 'partial'
                
            else:
                transaction.status = 'failed'
                transaction.failure_reason = intent.last_payment_error.message if intent.last_payment_error else 'Payment failed'
            
            transaction.gateway_response = json.dumps(intent.to_dict())
            self.db.session.commit()
            
            return transaction.status == 'completed'
            
        except Exception as e:
            logger.error(f"Failed to confirm Stripe payment: {str(e)}")
            return False
    
    # ==================== RAZORPAY INTEGRATION ====================
    
    def create_razorpay_order(self, bill_id, amount, currency='INR'):
        """Create Razorpay order"""
        try:
            if not self.razorpay_enabled:
                raise ValueError("Razorpay is not configured")
            
            from web_app import Bill
            bill = Bill.query.get(bill_id)
            if not bill:
                raise ValueError("Bill not found")
            
            # Create order
            order_data = {
                'amount': int(amount * 100),  # Razorpay uses paise
                'currency': currency,
                'receipt': f'bill_{bill_id}_{int(datetime.now().timestamp())}',
                'notes': {
                    'bill_id': str(bill_id),
                    'patient_id': str(bill.patient_id),
                    'patient_name': f"{bill.patient.first_name} {bill.patient.last_name}"
                }
            }
            
            order = self.razorpay_client.order.create(data=order_data)
            
            # Create transaction record
            transaction = self.PaymentTransaction(
                transaction_id=self._generate_transaction_id(),
                bill_id=bill_id,
                patient_id=bill.patient_id,
                gateway='razorpay',
                gateway_transaction_id=order['id'],
                amount=amount,
                currency=currency,
                status='pending'
            )
            
            self.db.session.add(transaction)
            self.db.session.commit()
            
            return {
                'order_id': order['id'],
                'transaction_id': transaction.transaction_id,
                'amount': amount,
                'currency': currency,
                'key': self.config['razorpay']['key_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            raise
    
    def verify_razorpay_payment(self, payment_data):
        """Verify Razorpay payment"""
        try:
            # Verify signature
            generated_signature = hmac.new(
                self.config['razorpay']['key_secret'].encode(),
                f"{payment_data['razorpay_order_id']}|{payment_data['razorpay_payment_id']}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            if generated_signature != payment_data['razorpay_signature']:
                raise ValueError("Invalid payment signature")
            
            # Get transaction
            transaction = self.PaymentTransaction.query.filter_by(
                gateway_transaction_id=payment_data['razorpay_order_id']
            ).first()
            
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Fetch payment details from Razorpay
            payment = self.razorpay_client.payment.fetch(payment_data['razorpay_payment_id'])
            
            if payment['status'] == 'captured':
                transaction.status = 'completed'
                transaction.completed_at = datetime.utcnow()
                transaction.payment_method = payment['method']
                
                # Update bill payment status (similar to Stripe)
                from web_app import Bill, Payment
                bill = Bill.query.get(transaction.bill_id)
                if bill:
                    payment_record = Payment(
                        bill_id=bill.id,
                        amount=transaction.amount,
                        payment_method='online',
                        transaction_id=payment_data['razorpay_payment_id'],
                        received_by=current_user.id if current_user.is_authenticated else None
                    )
                    
                    self.db.session.add(payment_record)
                    
                    bill.paid_amount += transaction.amount
                    bill.balance_amount = bill.total_amount - bill.paid_amount
                    
                    if bill.balance_amount <= 0:
                        bill.payment_status = 'paid'
                    elif bill.paid_amount > 0:
                        bill.payment_status = 'partial'
            else:
                transaction.status = 'failed'
                transaction.failure_reason = payment.get('error_description', 'Payment failed')
            
            transaction.gateway_response = json.dumps(payment)
            self.db.session.commit()
            
            return transaction.status == 'completed'
            
        except Exception as e:
            logger.error(f"Failed to verify Razorpay payment: {str(e)}")
            return False
    
    # ==================== PAYPAL INTEGRATION ====================
    
    def create_paypal_payment(self, bill_id, amount, currency='USD'):
        """Create PayPal payment"""
        try:
            if not self.paypal_enabled:
                raise ValueError("PayPal is not configured")
            
            from web_app import Bill
            bill = Bill.query.get(bill_id)
            if not bill:
                raise ValueError("Bill not found")
            
            # Create payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": f"{request.host_url}payment/paypal/success",
                    "cancel_url": f"{request.host_url}payment/paypal/cancel"
                },
                "transactions": [{
                    "item_list": {
                        "items": [{
                            "name": f"Medical Bill #{bill.bill_number}",
                            "sku": bill.bill_number,
                            "price": str(amount),
                            "currency": currency,
                            "quantity": 1
                        }]
                    },
                    "amount": {
                        "total": str(amount),
                        "currency": currency
                    },
                    "description": f"Payment for medical services - Bill #{bill.bill_number}"
                }]
            })
            
            if payment.create():
                # Create transaction record
                transaction = self.PaymentTransaction(
                    transaction_id=self._generate_transaction_id(),
                    bill_id=bill_id,
                    patient_id=bill.patient_id,
                    gateway='paypal',
                    gateway_transaction_id=payment.id,
                    amount=amount,
                    currency=currency,
                    status='pending'
                )
                
                self.db.session.add(transaction)
                self.db.session.commit()
                
                # Get approval URL
                approval_url = None
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = link.href
                        break
                
                return {
                    'payment_id': payment.id,
                    'transaction_id': transaction.transaction_id,
                    'approval_url': approval_url,
                    'amount': amount,
                    'currency': currency
                }
            else:
                raise ValueError(f"PayPal payment creation failed: {payment.error}")
            
        except Exception as e:
            logger.error(f"Failed to create PayPal payment: {str(e)}")
            raise
    
    def execute_paypal_payment(self, payment_id, payer_id):
        """Execute PayPal payment"""
        try:
            payment = paypalrestsdk.Payment.find(payment_id)
            
            if payment.execute({"payer_id": payer_id}):
                # Update transaction
                transaction = self.PaymentTransaction.query.filter_by(
                    gateway_transaction_id=payment_id
                ).first()
                
                if transaction:
                    transaction.status = 'completed'
                    transaction.completed_at = datetime.utcnow()
                    transaction.payment_method = 'paypal'
                    
                    # Update bill payment status
                    from web_app import Bill, Payment
                    bill = Bill.query.get(transaction.bill_id)
                    if bill:
                        payment_record = Payment(
                            bill_id=bill.id,
                            amount=transaction.amount,
                            payment_method='online',
                            transaction_id=payment_id,
                            received_by=current_user.id if current_user.is_authenticated else None
                        )
                        
                        self.db.session.add(payment_record)
                        
                        bill.paid_amount += transaction.amount
                        bill.balance_amount = bill.total_amount - bill.paid_amount
                        
                        if bill.balance_amount <= 0:
                            bill.payment_status = 'paid'
                        elif bill.paid_amount > 0:
                            bill.payment_status = 'partial'
                    
                    transaction.gateway_response = json.dumps(payment.to_dict())
                    self.db.session.commit()
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute PayPal payment: {str(e)}")
            return False
    
    # ==================== REFUND MANAGEMENT ====================
    
    def process_refund(self, transaction_id, amount, reason):
        """Process refund for a transaction"""
        try:
            transaction = self.PaymentTransaction.query.filter_by(
                transaction_id=transaction_id
            ).first()
            
            if not transaction:
                raise ValueError("Transaction not found")
            
            if transaction.status != 'completed':
                raise ValueError("Can only refund completed transactions")
            
            # Generate refund ID
            refund_id = self._generate_refund_id()
            
            # Process refund based on gateway
            success = False
            gateway_refund_id = None
            
            if transaction.gateway == 'stripe':
                success, gateway_refund_id = self._process_stripe_refund(transaction, amount)
            elif transaction.gateway == 'razorpay':
                success, gateway_refund_id = self._process_razorpay_refund(transaction, amount)
            elif transaction.gateway == 'paypal':
                success, gateway_refund_id = self._process_paypal_refund(transaction, amount)
            
            # Create refund record
            refund = self.PaymentRefund(
                refund_id=refund_id,
                transaction_id=transaction.id,
                amount=amount,
                reason=reason,
                gateway_refund_id=gateway_refund_id,
                status='completed' if success else 'failed',
                requested_by=current_user.id if current_user.is_authenticated else None,
                completed_at=datetime.utcnow() if success else None
            )
            
            self.db.session.add(refund)
            
            if success:
                # Update bill amounts
                from web_app import Bill
                bill = Bill.query.get(transaction.bill_id)
                if bill:
                    bill.paid_amount -= amount
                    bill.balance_amount += amount
                    
                    if bill.paid_amount <= 0:
                        bill.payment_status = 'pending'
                    elif bill.balance_amount > 0:
                        bill.payment_status = 'partial'
            
            self.db.session.commit()
            
            return success, refund_id
            
        except Exception as e:
            logger.error(f"Failed to process refund: {str(e)}")
            return False, None
    
    def _process_stripe_refund(self, transaction, amount):
        """Process Stripe refund"""
        try:
            refund = stripe.Refund.create(
                payment_intent=transaction.gateway_transaction_id,
                amount=int(amount * 100)
            )
            return refund.status == 'succeeded', refund.id
        except Exception as e:
            logger.error(f"Stripe refund failed: {str(e)}")
            return False, None
    
    def _process_razorpay_refund(self, transaction, amount):
        """Process Razorpay refund"""
        try:
            # First get the payment ID from the order
            order = self.razorpay_client.order.fetch(transaction.gateway_transaction_id)
            payments = self.razorpay_client.order.payments(transaction.gateway_transaction_id)
            
            if payments['items']:
                payment_id = payments['items'][0]['id']
                refund = self.razorpay_client.payment.refund(payment_id, int(amount * 100))
                return refund['status'] == 'processed', refund['id']
            
            return False, None
        except Exception as e:
            logger.error(f"Razorpay refund failed: {str(e)}")
            return False, None
    
    def _process_paypal_refund(self, transaction, amount):
        """Process PayPal refund"""
        try:
            payment = paypalrestsdk.Payment.find(transaction.gateway_transaction_id)
            
            # Find the sale transaction
            sale_id = None
            for transaction_detail in payment.transactions[0].related_resources:
                if 'sale' in transaction_detail:
                    sale_id = transaction_detail['sale']['id']
                    break
            
            if sale_id:
                sale = paypalrestsdk.Sale.find(sale_id)
                refund = sale.refund({
                    "amount": {
                        "total": str(amount),
                        "currency": transaction.currency
                    }
                })
                
                if refund.success():
                    return True, refund.id
            
            return False, None
        except Exception as e:
            logger.error(f"PayPal refund failed: {str(e)}")
            return False, None
    
    # ==================== UTILITY METHODS ====================
    
    def _generate_transaction_id(self):
        """Generate unique transaction ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"TXN{timestamp}{random_suffix.upper()}"
    
    def _generate_refund_id(self):
        """Generate unique refund ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:6]
        return f"REF{timestamp}{random_suffix.upper()}"
    
    def get_payment_methods(self):
        """Get available payment methods"""
        methods = []
        
        if self.stripe_enabled:
            methods.append({
                'id': 'stripe',
                'name': 'Credit/Debit Card (Stripe)',
                'description': 'Pay securely with your credit or debit card'
            })
        
        if self.razorpay_enabled:
            methods.append({
                'id': 'razorpay',
                'name': 'Multiple Payment Options (Razorpay)',
                'description': 'UPI, Net Banking, Cards, Wallets'
            })
        
        if self.paypal_enabled:
            methods.append({
                'id': 'paypal',
                'name': 'PayPal',
                'description': 'Pay with your PayPal account'
            })
        
        return methods
    
    def get_transaction_status(self, transaction_id):
        """Get transaction status"""
        transaction = self.PaymentTransaction.query.filter_by(
            transaction_id=transaction_id
        ).first()
        
        if not transaction:
            return None
        
        return {
            'transaction_id': transaction.transaction_id,
            'status': transaction.status,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'gateway': transaction.gateway,
            'created_at': transaction.created_at.isoformat(),
            'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None
        }

def init_payment_gateway(app, db):
    """Initialize payment gateway system"""
    return PaymentGateway(db, app)