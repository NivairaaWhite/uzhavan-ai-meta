from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.database import get_db
from app.models import CropListing, Order, OrderStatus, User, UserRole
from app.schemas import OrderCreate, OrderOut
from app.services.payments import razorpay_client, PaymentConfigError

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.BUYER)),
):
    listing = db.query(CropListing).filter(CropListing.id == payload.listing_id).first()
    if not listing or listing.status != "available":
        raise HTTPException(status_code=404, detail="Listing not available")
    if payload.quantity_kg > listing.quantity_kg:
        raise HTTPException(status_code=400, detail="Requested quantity exceeds listing")

    price = listing.fair_price_per_kg or listing.target_price_per_kg
    if not price:
        raise HTTPException(status_code=422, detail="Listing has no price set yet")
    total = round(price * payload.quantity_kg, 2)

    order = Order(
        listing_id=listing.id,
        buyer_id=user.id,
        quantity_kg=payload.quantity_kg,
        agreed_price_per_kg=price,
        total_amount=total,
        delivery_deadline=payload.delivery_deadline,
    )

    try:
        rp_order = await razorpay_client.create_order(total, receipt=f"order-{listing.id}")
        order.razorpay_order_id = rp_order["id"]
        order.status = OrderStatus.PENDING
    except PaymentConfigError:
        # Sandbox/dev without Razorpay keys configured: still create the
        # order record so the rest of the flow (matching, logistics) is
        # testable; it just stays PENDING until payments are configured.
        pass

    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/confirm-payment", response_model=OrderOut)
async def confirm_payment(
    order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    valid = await razorpay_client.verify_payment_signature(
        order.razorpay_order_id, razorpay_payment_id, razorpay_signature
    )
    if not valid:
        raise HTTPException(status_code=400, detail="Payment signature verification failed")
    order.razorpay_payment_id = razorpay_payment_id
    order.status = OrderStatus.ESCROW_HELD
    db.commit()
    db.refresh(order)
    return order


@router.get("/mine", response_model=List[OrderOut])
def my_orders(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Order).filter(Order.buyer_id == user.id).all()
