from datetime import datetime, timedelta
import random
import odoorpc
import argparse

### README
#
# The user that executes this script must have 
# 'user' level access for inventory
# 'access rights' level for administration
# Recommed running with admin account which have full access rights on every app


parser = argparse.ArgumentParser(prog="Odoo 13 Data Entry Script",
                                 description="Adds sale and purchase order to odoo",
                                 epilog="Written for ERP course, sem 2/25-26")

parser.add_argument('-y','--year',help="Number. Data will go from Jan 1 to Dec 31 of this year", required=True)
parser.add_argument('-n','--number', help="Number. Number of records to add. Must be less than 365. Defaults to 50", default=50)
parser.add_argument('--host', help="Hostname of the odoo instance. Defaults to locahost", default="localhost")
parser.add_argument('-p','--port', help='Number. The port number of the odoo instance. Defaults to 8069', default=8069)
parser.add_argument('-u','--user',help='Email of the account. Defaults to admin', default='admin')
parser.add_argument('-pw','--password', help='Password of the account.', required=True)
parser.add_argument('-d','--database', help='Database to connect to.', required=True)
parser.add_argument('-so','--sale-orders', help="Whether to add sale orders. Defaults to True", default=True)
parser.add_argument('-po','--purchase-orders', help="Whether to add purchase orders. Defaults to True", default=True)
parser.add_argument('-wh','--warehouse', help='Name of the main warehouse in odoo. Defaults to My Company', default='My Company')

args = parser.parse_args()
# generate a year worth of datetimes
YEAR = int(args.year)
NUMBER = int(args.number) # NUMBER of records to insert
HOST = str(args.host)
PORT = int(args.port)
USER = str(args.user)
PASSWORD = str(args.password)
DATABASE = str(args.database)
SALEORDER = bool(args.sale_orders)
PURCHASEORDER = bool(args.purchase_orders)
WAREHOUSE = str(args.warehouse)
DTFORMAT = '%Y-%m-%d %H:%M:%S'
DFORMAT = '%Y-%m-%d'

days = 366 if (YEAR%4)==0 else 365

date = datetime(YEAR, 1, 1)
dates = []
for i in range(days):
    dates.append(date)
    date = date + timedelta(days=1)
    

selected_dates = random.sample(dates, NUMBER)
selected_dates.sort()

# print(selected_dates)
# print(len(selected_dates))

odoo = odoorpc.ODOO(HOST, port=PORT)
odoo.login(DATABASE, USER, PASSWORD)

user = odoo.env.user
# print(user.name)
# print(user.id)

# Odoo models
Partner = odoo.env['res.partner']
Product = odoo.env['product.product']
SaleOrder = odoo.env['sale.order']
Picking = odoo.env['stock.picking']
StockMove = odoo.env['stock.move']
InvoiceWizard = odoo.env['sale.advance.payment.inv'] # for sale order invoices
Warehouse = odoo.env['stock.warehouse']
Invoice = odoo.env['account.move']
Employee = odoo.env['hr.employee']
PurchaseOrder = odoo.env['purchase.order']
AccMove = odoo.env['account.move']
Account = odoo.env['account.account']
PurchaseOrderLine = odoo.env['purchase.order.line']

# get customers and vendors
ids = Partner.search([])
customers = [] # companies/people who buy from us
vendors = [] # companies/people we buy raw materials from
for p in Partner.browse(ids):
    if(p.customer_rank > 0):
        customers.append(p)
    if(p.supplier_rank > 0):
        vendors.append(p)

# get warehouses
# we know that saigon brew has only 1 warehouse called Saigonbrew Warehouse
ids = Warehouse.search([('name','=',WAREHOUSE)])
warehouse = Warehouse.browse(ids)

# get products and raw materials
ids = Product.search([('purchase_ok','=',True),('name','!=','Tips')])
rawMaterials = []
for p in Product.browse(ids):
    rawMaterials.append(p)

ids = Product.search([('sale_ok','=',True),('name','!=','Tips'),('name','!=','Discount')
                      ,('available_in_pos','!=',True)])
saleProducts = []
for p in Product.browse(ids):
    saleProducts.append(p)

# get sale employees
ids = Employee.search([('active','=',True)])
saleEmployees = []
for e in Employee.browse(ids):
    if(e.department_id.name == 'Sales'):
        saleEmployees.append(e)

# generate sale orders first
if(SALEORDER):

    # loop NUMBER times
    for i in range(NUMBER):
        print('Writing Order #',i)
        customer = random.choice(customers)
        quantity = random.randint(10,100)
        date_order = selected_dates[i]
        product = random.choice(saleProducts)
        salePerson = random.choice(saleEmployees)

        
        
        saleOrderId = SaleOrder.create({
            'partner_id' : customer.id,
            'warehouse_id' : warehouse.id,
            'date_order' : date_order.strftime(DTFORMAT),
            'user_id' : salePerson.user_id.id,
            'order_line' : [(0,0,{
                'product_id' : product.id,
                'product_uom_qty' : quantity,
            })]
        })

        # confirm sale order
        SaleOrder.action_confirm([saleOrderId])

        # change the date to past dates
        delivery_date = (date_order+timedelta(days=5))

        SaleOrder.write([saleOrderId], {
            'date_order' : date_order.strftime(DTFORMAT),
            'commitment_date' : delivery_date.strftime(DTFORMAT)
            })
        
        # validate the delivery
        order_name = SaleOrder.browse(saleOrderId).name
        picking_ids = Picking.search([('origin','=',order_name),('state','!=','cancel')])

        for picking in Picking.browse(picking_ids):
            for move in picking.move_lines:
                move.write({
                    'is_done' : True
                    }) # this way we don't add or reduce our existing inventory

            picking.write({'state' : 'draft'})

            picking.write({
                'date_done' : delivery_date.strftime(DTFORMAT),
                'scheduled_date' : delivery_date.strftime(DTFORMAT)
                })
            
            picking.write({'state' : 'done'})
            
        # Create and post invoices
        wizard_id = InvoiceWizard.create({'advance_payment_method':'delivered'})
        context = {'active_model' : 'sale.order', 'active_ids' : [saleOrderId], 'active_id' : saleOrderId}
        InvoiceWizard.create_invoices([wizard_id], context=context)

        invoice_ids = Invoice.search([('invoice_origin','=',order_name),('state','=','draft')])

        inv_create_date = (delivery_date+timedelta(days=1)).strftime(DTFORMAT)
        inv_date = (delivery_date+timedelta(days=1)).strftime(DFORMAT)
        inv_date_due = (delivery_date+timedelta(days=15)).strftime(DFORMAT)
        if invoice_ids:
            Invoice.write(invoice_ids, {
                'invoice_date' : inv_date,
                'create_date' : inv_create_date,
                'date' : inv_date,
                'invoice_date_due' : inv_date_due
            })
            Invoice.action_post(invoice_ids)

print(f'Finished adding {NUMBER} of sales orders')

# get the expense account
bankAccount = Account.browse(Account.search([('name','=','Bank')]))

if(PURCHASEORDER):

    # loop number of times
    for i in range(NUMBER):
        print('Writing order #',i)
        vendor = random.choice(vendors)
        quantity = random.randint(10,10000)
        date_order = selected_dates[i]
        product = random.choice(rawMaterials)
        date_planned = (date_order+timedelta(days=7)).strftime(DTFORMAT)
        salePerson = random.choice(saleEmployees)

        purchaseOrderId = PurchaseOrder.create({
            'partner_id' : vendor.id,
            'picking_type_id' : warehouse.id,
            'date_order' : date_order.strftime(DTFORMAT),
            'user_id' : salePerson.user_id.id,
            'order_line' : [(0,0, {
                'product_id' : product.id,
                'name' : product.name,
                'product_qty' : quantity,
                'price_unit' : product.price,
                'date_planned' : date_planned,
                'product_uom' : product.uom_id.id
            })]
        })

        PurchaseOrder.button_confirm([purchaseOrderId])

        PurchaseOrder.write([purchaseOrderId], {
            'date_order' : date_order.strftime(DTFORMAT),
        })

        po_name = PurchaseOrder.browse(purchaseOrderId).name
        picking = Picking.search([('origin','=',po_name)])

        for picking in Picking.browse(picking):
            for move in picking.move_lines:
                move.write({'is_done' : True})

            picking.write({'state' : 'draft'})


            picking.write({
                'date_done' : date_planned,
                'scheduled_date' : date_planned
            })
        
            picking.write({'state' : 'done'})

        purchaseOrder = PurchaseOrder.browse(purchaseOrderId)

        purchaseOrderLine = PurchaseOrderLine.browse(PurchaseOrderLine.search([('order_id','=',purchaseOrderId)]))

        action = purchaseOrder.action_view_invoice()
        ctx = action['context']
        ctx.update({'type' : 'in_invoice', 'default_type': 'in_invoice'})

        bill_id = AccMove.with_context(ctx).create({
            'type' : 'in_invoice',
            'partner_id' : purchaseOrder.partner_id.id,
            'purchase_id' : purchaseOrder.id,
            'invoice_origin' : purchaseOrder.name,
            'invoice_line_ids' : [(0,0,{
                'product_id' : product.id,
                'name' : product.name,
                'quantity' : quantity,
                'price_unit' : product.price,
                'account_id' : bankAccount.id,
                'purchase_line_id' : purchaseOrderLine.id
            })]
        })

        invoice_date = (date_order+timedelta(days=25)).strftime(DFORMAT)
        
        AccMove.write([bill_id], {
            'invoice_date' : invoice_date,
            'invoice_date_due' : invoice_date
        })

        AccMove.action_post([bill_id])

print(f'Finished creating {NUMBER} purchase orders')
