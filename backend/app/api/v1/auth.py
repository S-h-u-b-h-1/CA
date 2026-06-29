from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.models import Organization, User, AuditLog
from app.schemas.schemas import (
    OrganizationCreate,
    Token,
    UserLogin,
    UserResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db)
):
    # Check if user email already registered
    existing_user = db.query(User).filter(User.email == payload.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered"
        )

    # 1. Create Organization
    org = Organization(
        organization_name=payload.organization_name,
        firm_type=payload.firm_type,
        GSTIN=payload.GSTIN,
        PAN=payload.PAN,
        address=payload.address,
        contact_email=payload.contact_email,
        phone=payload.phone,
        subscription_plan="Free"
    )
    db.add(org)
    db.flush()  # To populate org.id

    # 2. Create FIRM_ADMIN User
    hashed_pwd = hash_password(payload.admin_password)
    user = User(
        organization_id=org.id,
        email=payload.admin_email,
        hashed_password=hashed_pwd,
        first_name=payload.admin_first_name,
        last_name=payload.admin_last_name,
        role="FIRM_ADMIN",
        is_active=True
    )
    db.add(user)
    db.flush()

    # 3. Create Audit Log
    audit = AuditLog(
        organization_id=org.id,
        user_id=user.id,
        action="ORG_REGISTRATION",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        details=f"Registered organization {org.organization_name} and admin {user.email}"
    )
    db.add(audit)
    db.commit()
    db.refresh(user)

    # 4. Generate Access Token
    access_token = create_access_token(subject=user.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/login", response_model=Token)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == payload.email,
        User.deleted_at.is_(None)
    ).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Audit log login
    audit = AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=user.id,
        details=f"User {user.email} successfully logged in"
    )
    db.add(audit)
    db.commit()

    access_token = create_access_token(subject=user.email)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


# Organization routes
org_router = APIRouter()

@org_router.get("/profile", response_model=OrganizationResponse)
def get_organization_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org


@org_router.put("/profile", response_model=OrganizationResponse)
def update_organization_profile(
    payload: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only firm administrators or partners can update organization details
    if current_user.role not in ["FIRM_ADMIN", "PARTNER", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update organization profile"
        )

    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(org, field, value)
    
    # Audit log
    audit = AuditLog(
        organization_id=org.id,
        user_id=current_user.id,
        action="ORG_UPDATE",
        entity_type="ORGANIZATION",
        entity_id=org.id,
        details=f"Updated fields: {list(update_data.keys())}"
    )
    db.add(audit)
    db.commit()
    db.refresh(org)
    return org
