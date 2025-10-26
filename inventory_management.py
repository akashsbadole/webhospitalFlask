#!/usr/bin/env python3
"""
Advanced Inventory Management System
Handles purchase orders, suppliers, transfers, reorder points, valuation, and expiry tracking
"""

import json
import logging
from datetime import datetime, timedelta, date
from flask import current_app, request
from flask_login import current_user
from enum import Enum
import barcode
from barcode.writer import ImageWriter
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InventoryMethod(Enum):
    FIFO = "fifo"  # First In, First Out
    LIFO = "lifo"  # Last In, First Out
    WEIGHTED_AVERAGE = "weighted_average"

class PurchaseOrderStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    ORDERED = "ordered"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class InventoryManagement:
    def __init__(self, db, app):
        self.db = db
        self.app = app
        self.setup_inventory_tables()
        
        # Configuration
        self.config = {
            'valuation_method': InventoryMethod.FIFO,
            'auto_reorder_enabled': True,
            'expiry_alert_days': [30, 7, 1],  # Days before expiry to alert
            'low_stock_threshold_percentage': 20,  # % of min stock level
            'barcode_enabled': True,
            'multi_location_enabled': True
        }
    
    def setup_inventory_tables(self):
        """Create inventory management tables"""
        
        class Supplier(self.db.Model):
            __tablename__ = 'suppliers'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            supplier_code = self.db.Column(self.db.String(20), unique=True, nullable=False)
            name = self.db.Column(self.db.String(100), nullable=False)
            
            # Contact information
            contact_person = self.db.Column(self.db.String(100))
            phone = self.db.Column(self.db.String(20))
            email = self.db.Column(self.db.String(120))
            address = self.db.Column(self.db.Text)
            city = self.db.Column(self.db.String(50))
            state = self.db.Column(self.db.String(50))
            zip_code = self.db.Column(self.db.String(10))
            country = self.db.Column(self.db.String(50))
            
            # Business details
            tax_id = self.db.Column(self.db.String(50))
            payment_terms = self.db.Column(self.db.String(50))  # Net 30, Net 60, etc.
            credit_limit = self.db.Column(self.db.Float)
            
            # Performance metrics
            rating = self.db.Column(self.db.Float, default=5.0)  # 1-5 rating
            delivery_performance = self.db.Column(self.db.Float, default=100.0)  # Percentage
            
            # Status
            is_active = self.db.Column(self.db.Boolean, default=True)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
        
        class InventoryLocation(self.db.Model):
            __tablename__ = 'inventory_locations'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            location_code = self.db.Column(self.db.String(20), unique=True, nullable=False)
            name = self.db.Column(self.db.String(100), nullable=False)
            description = self.db.Column(self.db.Text)
            
            # Location details
            building = self.db.Column(self.db.String(50))
            floor = self.db.Column(self.db.String(20))
            room = self.db.Column(self.db.String(20))
            
            # Capacity and restrictions
            max_capacity = self.db.Column(self.db.Float)
            temperature_controlled = self.db.Column(self.db.Boolean, default=False)
            humidity_controlled = self.db.Column(self.db.Boolean, default=False)
            security_level = self.db.Column(self.db.String(20), default='standard')
            
            # Manager
            manager_id = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Status
            is_active = self.db.Column(self.db.Boolean, default=True)
            
            # Relationships
            manager = self.db.relationship('WebUser', backref='managed_locations')
        
        class ItemCategory(self.db.Model):
            __tablename__ = 'item_categories'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            name = self.db.Column(self.db.String(100), nullable=False)
            code = self.db.Column(self.db.String(20), unique=True, nullable=False)
            description = self.db.Column(self.db.Text)
            parent_category_id = self.db.Column(self.db.Integer, self.db.ForeignKey('item_categories.id'))
            
            # Properties
            requires_expiry_tracking = self.db.Column(self.db.Boolean, default=False)
            requires_batch_tracking = self.db.Column(self.db.Boolean, default=False)
            requires_serial_tracking = self.db.Column(self.db.Boolean, default=False)
            
            # Relationships
            parent_category = self.db.relationship('ItemCategory', remote_side=[id], backref='subcategories')
        
        class InventoryItem(self.db.Model):
            __tablename__ = 'inventory_items'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            item_code = self.db.Column(self.db.String(50), unique=True, nullable=False)
            name = self.db.Column(self.db.String(200), nullable=False)
            description = self.db.Column(self.db.Text)
            
            # Classification
            category_id = self.db.Column(self.db.Integer, self.db.ForeignKey('item_categories.id'))
            manufacturer = self.db.Column(self.db.String(100))
            brand = self.db.Column(self.db.String(100))
            
            # Units and measurements
            unit_of_measure = self.db.Column(self.db.String(20), nullable=False)  # pieces, kg, liters, etc.
            pack_size = self.db.Column(self.db.Integer, default=1)
            
            # Stock levels
            min_stock_level = self.db.Column(self.db.Float, default=0)
            max_stock_level = self.db.Column(self.db.Float, default=1000)
            reorder_point = self.db.Column(self.db.Float, default=0)
            reorder_quantity = self.db.Column(self.db.Float, default=0)
            
            # Pricing
            standard_cost = self.db.Column(self.db.Float, default=0)
            average_cost = self.db.Column(self.db.Float, default=0)
            last_purchase_cost = self.db.Column(self.db.Float, default=0)
            
            # Properties
            is_controlled_substance = self.db.Column(self.db.Boolean, default=False)
            requires_prescription = self.db.Column(self.db.Boolean, default=False)
            is_hazardous = self.db.Column(self.db.Boolean, default=False)
            
            # Barcode
            barcode_data = self.db.Column(self.db.String(100))
            
            # Status
            is_active = self.db.Column(self.db.Boolean, default=True)
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            
            # Relationships
            category = self.db.relationship('ItemCategory', backref='items')
        
        class InventoryStock(self.db.Model):
            __tablename__ = 'inventory_stock'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            item_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_items.id'), nullable=False)
            location_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_locations.id'), nullable=False)
            
            # Stock information
            quantity_on_hand = self.db.Column(self.db.Float, default=0)
            quantity_reserved = self.db.Column(self.db.Float, default=0)  # Reserved for orders
            quantity_available = self.db.Column(self.db.Float, default=0)  # On hand - reserved
            
            # Batch/Lot tracking
            batch_number = self.db.Column(self.db.String(50))
            lot_number = self.db.Column(self.db.String(50))
            serial_numbers = self.db.Column(self.db.Text)  # JSON array for serialized items
            
            # Expiry tracking
            expiry_date = self.db.Column(self.db.Date)
            manufacture_date = self.db.Column(self.db.Date)
            
            # Cost tracking
            unit_cost = self.db.Column(self.db.Float, default=0)
            total_value = self.db.Column(self.db.Float, default=0)
            
            # Audit
            last_counted = self.db.Column(self.db.DateTime)
            last_updated = self.db.Column(self.db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            
            # Relationships
            item = self.db.relationship('InventoryItem', backref='stock_records')
            location = self.db.relationship('InventoryLocation', backref='stock_records')
        
        class PurchaseOrder(self.db.Model):
            __tablename__ = 'purchase_orders'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            po_number = self.db.Column(self.db.String(50), unique=True, nullable=False)
            supplier_id = self.db.Column(self.db.Integer, self.db.ForeignKey('suppliers.id'), nullable=False)
            
            # Order details
            order_date = self.db.Column(self.db.Date, default=date.today)
            expected_delivery_date = self.db.Column(self.db.Date)
            actual_delivery_date = self.db.Column(self.db.Date)
            
            # Financial
            subtotal = self.db.Column(self.db.Float, default=0)
            tax_amount = self.db.Column(self.db.Float, default=0)
            shipping_cost = self.db.Column(self.db.Float, default=0)
            total_amount = self.db.Column(self.db.Float, default=0)
            
            # Status
            status = self.db.Column(self.db.String(20), default=PurchaseOrderStatus.DRAFT.value)
            
            # Personnel
            created_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            approved_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            received_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Notes
            notes = self.db.Column(self.db.Text)
            terms_and_conditions = self.db.Column(self.db.Text)
            
            # Audit
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            approved_at = self.db.Column(self.db.DateTime)
            
            # Relationships
            supplier = self.db.relationship('Supplier', backref='purchase_orders')
            creator = self.db.relationship('WebUser', foreign_keys=[created_by])
            approver = self.db.relationship('WebUser', foreign_keys=[approved_by])
            receiver = self.db.relationship('WebUser', foreign_keys=[received_by])
        
        class PurchaseOrderItem(self.db.Model):
            __tablename__ = 'purchase_order_items'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            po_id = self.db.Column(self.db.Integer, self.db.ForeignKey('purchase_orders.id'), nullable=False)
            item_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_items.id'), nullable=False)
            
            # Order details
            quantity_ordered = self.db.Column(self.db.Float, nullable=False)
            quantity_received = self.db.Column(self.db.Float, default=0)
            unit_price = self.db.Column(self.db.Float, nullable=False)
            total_price = self.db.Column(self.db.Float, nullable=False)
            
            # Delivery
            expected_date = self.db.Column(self.db.Date)
            
            # Relationships
            purchase_order = self.db.relationship('PurchaseOrder', backref='items')
            item = self.db.relationship('InventoryItem', backref='purchase_order_items')
        
        class StockMovement(self.db.Model):
            __tablename__ = 'stock_movements'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            item_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_items.id'), nullable=False)
            location_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_locations.id'), nullable=False)
            
            # Movement details
            movement_type = self.db.Column(self.db.String(20), nullable=False)  # receipt, issue, transfer, adjustment
            quantity = self.db.Column(self.db.Float, nullable=False)  # Positive for in, negative for out
            unit_cost = self.db.Column(self.db.Float, default=0)
            
            # Reference
            reference_type = self.db.Column(self.db.String(20))  # po, transfer, adjustment, etc.
            reference_id = self.db.Column(self.db.Integer)
            reference_number = self.db.Column(self.db.String(50))
            
            # Batch/Lot
            batch_number = self.db.Column(self.db.String(50))
            expiry_date = self.db.Column(self.db.Date)
            
            # Audit
            created_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            created_at = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            notes = self.db.Column(self.db.Text)
            
            # Relationships
            item = self.db.relationship('InventoryItem', backref='movements')
            location = self.db.relationship('InventoryLocation', backref='movements')
            creator = self.db.relationship('WebUser', backref='created_movements')
        
        class StockTransfer(self.db.Model):
            __tablename__ = 'stock_transfers'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            transfer_number = self.db.Column(self.db.String(50), unique=True, nullable=False)
            
            # Locations
            from_location_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_locations.id'), nullable=False)
            to_location_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_locations.id'), nullable=False)
            
            # Status
            status = self.db.Column(self.db.String(20), default='pending')  # pending, in_transit, completed, cancelled
            
            # Personnel
            requested_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            approved_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            shipped_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            received_by = self.db.Column(self.db.Integer, self.db.ForeignKey('web_user.id'))
            
            # Dates
            requested_date = self.db.Column(self.db.DateTime, default=datetime.utcnow)
            approved_date = self.db.Column(self.db.DateTime)
            shipped_date = self.db.Column(self.db.DateTime)
            received_date = self.db.Column(self.db.DateTime)
            
            # Notes
            notes = self.db.Column(self.db.Text)
            
            # Relationships
            from_location = self.db.relationship('InventoryLocation', foreign_keys=[from_location_id])
            to_location = self.db.relationship('InventoryLocation', foreign_keys=[to_location_id])
            requester = self.db.relationship('WebUser', foreign_keys=[requested_by])
        
        class StockTransferItem(self.db.Model):
            __tablename__ = 'stock_transfer_items'
            
            id = self.db.Column(self.db.Integer, primary_key=True)
            transfer_id = self.db.Column(self.db.Integer, self.db.ForeignKey('stock_transfers.id'), nullable=False)
            item_id = self.db.Column(self.db.Integer, self.db.ForeignKey('inventory_items.id'), nullable=False)
            
            # Quantities
            quantity_requested = self.db.Column(self.db.Float, nullable=False)
            quantity_shipped = self.db.Column(self.db.Float, default=0)
            quantity_received = self.db.Column(self.db.Float, default=0)
            
            # Batch tracking
            batch_number = self.db.Column(self.db.String(50))
            expiry_date = self.db.Column(self.db.Date)
            
            # Relationships
            transfer = self.db.relationship('StockTransfer', backref='items')
            item = self.db.relationship('InventoryItem', backref='transfer_items')
        
        # Store model classes
        self.Supplier = Supplier
        self.InventoryLocation = InventoryLocation
        self.ItemCategory = ItemCategory
        self.InventoryItem = InventoryItem
        self.InventoryStock = InventoryStock
        self.PurchaseOrder = PurchaseOrder
        self.PurchaseOrderItem = PurchaseOrderItem
        self.StockMovement = StockMovement
        self.StockTransfer = StockTransfer
        self.StockTransferItem = StockTransferItem
        
        # Create tables
        self.db.create_all()
        self._create_default_data()
    
    def _create_default_data(self):
        """Create default categories and locations"""
        # Default categories
        default_categories = [
            {'name': 'Medicines', 'code': 'MED', 'requires_expiry_tracking': True, 'requires_batch_tracking': True},
            {'name': 'Medical Supplies', 'code': 'SUP', 'requires_expiry_tracking': False, 'requires_batch_tracking': False},
            {'name': 'Equipment', 'code': 'EQP', 'requires_serial_tracking': True},
            {'name': 'Consumables', 'code': 'CON', 'requires_expiry_tracking': True}
        ]
        
        for cat_data in default_categories:
            existing = self.ItemCategory.query.filter_by(code=cat_data['code']).first()
            if not existing:
                category = self.ItemCategory(**cat_data)
                self.db.session.add(category)
        
        # Default locations
        default_locations = [
            {'location_code': 'MAIN', 'name': 'Main Pharmacy', 'building': 'Main', 'floor': 'Ground'},
            {'location_code': 'EMER', 'name': 'Emergency Store', 'building': 'Emergency', 'floor': 'Ground'},
            {'location_code': 'WARD', 'name': 'Ward Store', 'building': 'Main', 'floor': '1st'}
        ]
        
        for loc_data in default_locations:
            existing = self.InventoryLocation.query.filter_by(location_code=loc_data['location_code']).first()
            if not existing:
                location = self.InventoryLocation(**loc_data)
                self.db.session.add(location)
        
        try:
            self.db.session.commit()
        except Exception as e:
            logger.error(f"Failed to create default data: {str(e)}")
            self.db.session.rollback()
    
    # ==================== ITEM MANAGEMENT ====================
    
    def create_inventory_item(self, item_data):
        """Create new inventory item"""
        try:
            # Generate item code if not provided
            if not item_data.get('item_code'):
                item_data['item_code'] = self._generate_item_code(item_data.get('category_id'))
            
            # Generate barcode if enabled
            if self.config['barcode_enabled']:
                item_data['barcode_data'] = self._generate_barcode(item_data['item_code'])
            
            # Create item
            item = self.InventoryItem(**item_data)
            self.db.session.add(item)
            self.db.session.commit()
            
            # Create initial stock records for all locations
            locations = self.InventoryLocation.query.filter_by(is_active=True).all()
            for location in locations:
                stock = self.InventoryStock(
                    item_id=item.id,
                    location_id=location.id,
                    quantity_on_hand=0,
                    quantity_available=0
                )
                self.db.session.add(stock)
            
            self.db.session.commit()
            
            logger.info(f"Created inventory item: {item.item_code}")
            return item
            
        except Exception as e:
            logger.error(f"Failed to create inventory item: {str(e)}")
            self.db.session.rollback()
            raise
    
    def update_stock_levels(self, item_id, location_id, quantity_change, 
                          movement_type, unit_cost=0, batch_number=None, 
                          expiry_date=None, reference_type=None, reference_id=None):
        """Update stock levels and record movement"""
        try:
            # Get or create stock record
            stock = self.InventoryStock.query.filter_by(
                item_id=item_id,
                location_id=location_id
            ).first()
            
            if not stock:
                stock = self.InventoryStock(
                    item_id=item_id,
                    location_id=location_id,
                    quantity_on_hand=0,
                    quantity_available=0
                )
                self.db.session.add(stock)
            
            # Update quantities
            stock.quantity_on_hand += quantity_change
            stock.quantity_available = stock.quantity_on_hand - stock.quantity_reserved
            
            # Update costs using configured method
            if quantity_change > 0 and unit_cost > 0:  # Incoming stock
                self._update_item_costs(item_id, quantity_change, unit_cost)
                stock.unit_cost = unit_cost
            
            stock.total_value = stock.quantity_on_hand * stock.unit_cost
            stock.last_updated = datetime.utcnow()
            
            # Record movement
            movement = self.StockMovement(
                item_id=item_id,
                location_id=location_id,
                movement_type=movement_type,
                quantity=quantity_change,
                unit_cost=unit_cost,
                reference_type=reference_type,
                reference_id=reference_id,
                batch_number=batch_number,
                expiry_date=expiry_date,
                created_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(movement)
            self.db.session.commit()
            
            # Check for reorder alerts
            if quantity_change < 0:  # Stock going out
                self._check_reorder_point(item_id, location_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update stock levels: {str(e)}")
            self.db.session.rollback()
            return False
    
    def _update_item_costs(self, item_id, quantity, unit_cost):
        """Update item costs based on valuation method"""
        try:
            item = self.db.session.get(self.InventoryItem, item_id)
            if not item:
                return
            
            if self.config['valuation_method'] == InventoryMethod.FIFO:
                # For FIFO, we track costs per batch
                item.last_purchase_cost = unit_cost
            
            elif self.config['valuation_method'] == InventoryMethod.WEIGHTED_AVERAGE:
                # Calculate weighted average
                total_stock = sum(s.quantity_on_hand for s in item.stock_records)
                total_value = sum(s.total_value for s in item.stock_records)
                
                new_total_quantity = total_stock + quantity
                new_total_value = total_value + (quantity * unit_cost)
                
                if new_total_quantity > 0:
                    item.average_cost = new_total_value / new_total_quantity
            
            item.last_purchase_cost = unit_cost
            
        except Exception as e:
            logger.error(f"Failed to update item costs: {str(e)}")
    
    # ==================== PURCHASE ORDER MANAGEMENT ====================
    
    def create_purchase_order(self, supplier_id, items_data, expected_delivery_date=None):
        """Create new purchase order"""
        try:
            # Generate PO number
            po_number = self._generate_po_number()
            
            # Create purchase order
            po = self.PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier_id,
                expected_delivery_date=expected_delivery_date,
                created_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(po)
            self.db.session.flush()  # Get PO ID
            
            # Add items
            subtotal = 0
            for item_data in items_data:
                po_item = self.PurchaseOrderItem(
                    po_id=po.id,
                    item_id=item_data['item_id'],
                    quantity_ordered=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    total_price=item_data['quantity'] * item_data['unit_price'],
                    expected_date=item_data.get('expected_date')
                )
                
                self.db.session.add(po_item)
                subtotal += po_item.total_price
            
            # Calculate totals
            po.subtotal = subtotal
            po.tax_amount = subtotal * 0.1  # 10% tax (configurable)
            po.total_amount = po.subtotal + po.tax_amount
            
            self.db.session.commit()
            
            logger.info(f"Created purchase order: {po_number}")
            return po
            
        except Exception as e:
            logger.error(f"Failed to create purchase order: {str(e)}")
            self.db.session.rollback()
            raise
    
    def approve_purchase_order(self, po_id, notes=None):
        """Approve purchase order"""
        try:
            po = self.PurchaseOrder.query.get(po_id)
            if not po:
                raise ValueError("Purchase order not found")
            
            if po.status != PurchaseOrderStatus.DRAFT.value:
                raise ValueError("Only draft orders can be approved")
            
            po.status = PurchaseOrderStatus.APPROVED.value
            po.approved_by = current_user.id if current_user.is_authenticated else None
            po.approved_at = datetime.utcnow()
            
            if notes:
                po.notes = f"{po.notes}\n\nApproval Notes: {notes}" if po.notes else f"Approval Notes: {notes}"
            
            self.db.session.commit()
            
            logger.info(f"Purchase order approved: {po.po_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve purchase order: {str(e)}")
            return False
    
    def receive_purchase_order(self, po_id, received_items):
        """Receive items from purchase order"""
        try:
            po = self.PurchaseOrder.query.get(po_id)
            if not po:
                raise ValueError("Purchase order not found")
            
            for received_item in received_items:
                po_item = self.PurchaseOrderItem.query.get(received_item['po_item_id'])
                if not po_item:
                    continue
                
                quantity_received = received_item['quantity_received']
                location_id = received_item['location_id']
                batch_number = received_item.get('batch_number')
                expiry_date = received_item.get('expiry_date')
                
                # Update PO item
                po_item.quantity_received += quantity_received
                
                # Update stock
                self.update_stock_levels(
                    item_id=po_item.item_id,
                    location_id=location_id,
                    quantity_change=quantity_received,
                    movement_type='receipt',
                    unit_cost=po_item.unit_price,
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    reference_type='po',
                    reference_id=po.id
                )
            
            # Check if PO is fully received
            all_received = all(
                item.quantity_received >= item.quantity_ordered
                for item in po.items
            )
            
            if all_received:
                po.status = PurchaseOrderStatus.RECEIVED.value
                po.actual_delivery_date = date.today()
                po.received_by = current_user.id if current_user.is_authenticated else None
            
            self.db.session.commit()
            
            logger.info(f"Received items for PO: {po.po_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to receive purchase order: {str(e)}")
            self.db.session.rollback()
            return False
    
    # ==================== STOCK TRANSFER MANAGEMENT ====================
    
    def create_stock_transfer(self, from_location_id, to_location_id, items_data):
        """Create stock transfer between locations"""
        try:
            # Generate transfer number
            transfer_number = self._generate_transfer_number()
            
            # Create transfer
            transfer = self.StockTransfer(
                transfer_number=transfer_number,
                from_location_id=from_location_id,
                to_location_id=to_location_id,
                requested_by=current_user.id if current_user.is_authenticated else None
            )
            
            self.db.session.add(transfer)
            self.db.session.flush()
            
            # Add items
            for item_data in items_data:
                transfer_item = self.StockTransferItem(
                    transfer_id=transfer.id,
                    item_id=item_data['item_id'],
                    quantity_requested=item_data['quantity'],
                    batch_number=item_data.get('batch_number'),
                    expiry_date=item_data.get('expiry_date')
                )
                
                self.db.session.add(transfer_item)
            
            self.db.session.commit()
            
            logger.info(f"Created stock transfer: {transfer_number}")
            return transfer
            
        except Exception as e:
            logger.error(f"Failed to create stock transfer: {str(e)}")
            self.db.session.rollback()
            raise
    
    def process_stock_transfer(self, transfer_id, action='ship'):
        """Process stock transfer (ship or receive)"""
        try:
            transfer = self.StockTransfer.query.get(transfer_id)
            if not transfer:
                raise ValueError("Transfer not found")
            
            if action == 'ship':
                # Ship items (remove from source location)
                for item in transfer.items:
                    self.update_stock_levels(
                        item_id=item.item_id,
                        location_id=transfer.from_location_id,
                        quantity_change=-item.quantity_requested,
                        movement_type='transfer_out',
                        reference_type='transfer',
                        reference_id=transfer.id,
                        batch_number=item.batch_number
                    )
                    
                    item.quantity_shipped = item.quantity_requested
                
                transfer.status = 'in_transit'
                transfer.shipped_by = current_user.id if current_user.is_authenticated else None
                transfer.shipped_date = datetime.utcnow()
            
            elif action == 'receive':
                # Receive items (add to destination location)
                for item in transfer.items:
                    self.update_stock_levels(
                        item_id=item.item_id,
                        location_id=transfer.to_location_id,
                        quantity_change=item.quantity_shipped,
                        movement_type='transfer_in',
                        reference_type='transfer',
                        reference_id=transfer.id,
                        batch_number=item.batch_number,
                        expiry_date=item.expiry_date
                    )
                    
                    item.quantity_received = item.quantity_shipped
                
                transfer.status = 'completed'
                transfer.received_by = current_user.id if current_user.is_authenticated else None
                transfer.received_date = datetime.utcnow()
            
            self.db.session.commit()
            
            logger.info(f"Processed transfer {transfer.transfer_number}: {action}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process stock transfer: {str(e)}")
            self.db.session.rollback()
            return False
    
    # ==================== ALERTS AND MONITORING ====================
    
    def check_low_stock_items(self):
        """Check for items below reorder point"""
        try:
            low_stock_items = []
            
            # Get all active items
            items = self.InventoryItem.query.filter_by(is_active=True).all()
            
            for item in items:
                total_stock = sum(s.quantity_available for s in item.stock_records)
                
                if total_stock <= item.reorder_point:
                    low_stock_items.append({
                        'item_id': item.id,
                        'item_code': item.item_code,
                        'name': item.name,
                        'current_stock': total_stock,
                        'reorder_point': item.reorder_point,
                        'reorder_quantity': item.reorder_quantity
                    })
            
            return low_stock_items
            
        except Exception as e:
            logger.error(f"Failed to check low stock items: {str(e)}")
            return []
    
    def check_expiring_items(self, days_ahead=30):
        """Check for items expiring soon"""
        try:
            expiry_date = date.today() + timedelta(days=days_ahead)
            
            expiring_items = self.InventoryStock.query.filter(
                self.InventoryStock.expiry_date <= expiry_date,
                self.InventoryStock.expiry_date >= date.today(),
                self.InventoryStock.quantity_on_hand > 0
            ).all()
            
            return [
                {
                    'item_code': stock.item.item_code,
                    'name': stock.item.name,
                    'location': stock.location.name,
                    'quantity': stock.quantity_on_hand,
                    'expiry_date': stock.expiry_date.isoformat(),
                    'days_to_expiry': (stock.expiry_date - date.today()).days,
                    'batch_number': stock.batch_number
                }
                for stock in expiring_items
            ]
            
        except Exception as e:
            logger.error(f"Failed to check expiring items: {str(e)}")
            return []
    
    def _check_reorder_point(self, item_id, location_id):
        """Check if item has reached reorder point"""
        try:
            item = self.InventoryItem.query.get(item_id)
            if not item or not self.config['auto_reorder_enabled']:
                return
            
            total_stock = sum(s.quantity_available for s in item.stock_records)
            
            if total_stock <= item.reorder_point and item.reorder_quantity > 0:
                # Create automatic reorder suggestion
                logger.info(f"Item {item.item_code} has reached reorder point. Current stock: {total_stock}, Reorder point: {item.reorder_point}")
                
                # In a real system, this might create a purchase requisition
                # or send notifications to procurement team
            
        except Exception as e:
            logger.error(f"Failed to check reorder point: {str(e)}")
    
    # ==================== UTILITY METHODS ====================
    
    def _generate_item_code(self, category_id):
        """Generate unique item code"""
        try:
            category = self.ItemCategory.query.get(category_id) if category_id else None
            prefix = category.code if category else 'ITM'
            
            # Get next sequence number
            last_item = self.InventoryItem.query.filter(
                self.InventoryItem.item_code.like(f'{prefix}%')
            ).order_by(self.InventoryItem.item_code.desc()).first()
            
            if last_item:
                last_number = int(last_item.item_code[len(prefix):])
                next_number = last_number + 1
            else:
                next_number = 1
            
            return f"{prefix}{next_number:06d}"
            
        except Exception as e:
            logger.error(f"Failed to generate item code: {str(e)}")
            return f"ITM{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _generate_po_number(self):
        """Generate unique purchase order number"""
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Get count of POs today
        today_count = self.PurchaseOrder.query.filter(
            self.PurchaseOrder.po_number.like(f'PO{timestamp}%')
        ).count()
        
        return f"PO{timestamp}{today_count + 1:03d}"
    
    def _generate_transfer_number(self):
        """Generate unique transfer number"""
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Get count of transfers today
        today_count = self.StockTransfer.query.filter(
            self.StockTransfer.transfer_number.like(f'TR{timestamp}%')
        ).count()
        
        return f"TR{timestamp}{today_count + 1:03d}"
    
    def _generate_barcode(self, item_code):
        """Generate barcode for item"""
        try:
            if not self.config['barcode_enabled']:
                return None
            
            # Generate Code128 barcode
            code128 = barcode.get_barcode_class('code128')
            barcode_instance = code128(item_code, writer=ImageWriter())
            
            # Convert to base64 for storage/display
            buffer = io.BytesIO()
            barcode_instance.write(buffer)
            buffer.seek(0)
            
            barcode_base64 = base64.b64encode(buffer.getvalue()).decode()
            return barcode_base64
            
        except Exception as e:
            logger.error(f"Failed to generate barcode: {str(e)}")
            return None
    
    def get_inventory_valuation_report(self, location_id=None, category_id=None):
        """Generate inventory valuation report"""
        try:
            query = self.InventoryStock.query.join(self.InventoryItem)
            
            if location_id:
                query = query.filter(self.InventoryStock.location_id == location_id)
            
            if category_id:
                query = query.filter(self.InventoryItem.category_id == category_id)
            
            stock_records = query.filter(self.InventoryStock.quantity_on_hand > 0).all()
            
            total_value = 0
            items_data = []
            
            for stock in stock_records:
                item_value = stock.quantity_on_hand * stock.unit_cost
                total_value += item_value
                
                items_data.append({
                    'item_code': stock.item.item_code,
                    'name': stock.item.name,
                    'location': stock.location.name,
                    'quantity': stock.quantity_on_hand,
                    'unit_cost': stock.unit_cost,
                    'total_value': item_value,
                    'category': stock.item.category.name if stock.item.category else 'Uncategorized'
                })
            
            return {
                'total_value': total_value,
                'total_items': len(items_data),
                'items': items_data,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate valuation report: {str(e)}")
            return {}

def init_inventory_management(app, db):
    """Initialize inventory management system"""
    return InventoryManagement(db, app)