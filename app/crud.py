from sqlalchemy.orm import Session
from app import models
from app.schemas import ContactRequest
from datetime import datetime

def identify(payload: ContactRequest, db: Session):
    email = payload.email
    phone = payload.phoneNumber

    # Step 1: Find all matching contacts
    matched_contacts = db.query(models.Contact).filter(
        (models.Contact.email == email) | (models.Contact.phoneNumber == phone)
    ).all()

    if not matched_contacts:
        # Create new primary contact
        new_contact = models.Contact(
            email=email,
            phoneNumber=phone,
            linkPrecedence="primary",
        )
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        return {
            "contact": {
                "primaryContactId": new_contact.id,
                "emails": [email] if email else [],
                "phoneNumbers": [phone] if phone else [],
                "secondaryContactIds": [],
            }
        }

    # Step 2: Get all related groups (via both email and phone)
    related_primary_ids = set()
    for contact in matched_contacts:
        if contact.linkPrecedence == "primary":
            related_primary_ids.add(contact.id)
        else:
            related_primary_ids.add(contact.linkedId)

    # Fetch all contacts from all related groups
    all_related_contacts = db.query(models.Contact).filter(
        (models.Contact.id.in_(related_primary_ids)) | (models.Contact.linkedId.in_(related_primary_ids))
    ).all()

    # Step 3: Merge groups if needed
    primary_contacts = [c for c in all_related_contacts if c.linkPrecedence == "primary"]
    primary_contact = min(primary_contacts, key=lambda c: c.createdAt)
    primary_id = primary_contact.id

    for contact in primary_contacts:
        if contact.id != primary_id:
            contact.linkPrecedence = "secondary"
            contact.linkedId = primary_id
            contact.updatedAt = datetime.utcnow()
            db.add(contact)

    for contact in all_related_contacts:
        if contact.linkPrecedence == "secondary" and contact.linkedId != primary_id:
            contact.linkedId = primary_id
            contact.updatedAt = datetime.utcnow()
            db.add(contact)

    db.commit()

    # Refresh group after merge
    all_contacts = db.query(models.Contact).filter(
        (models.Contact.id == primary_id) | (models.Contact.linkedId == primary_id)
    ).all()

    # Step 4: Check if the request is already covered
    emails = set(c.email for c in all_contacts if c.email)
    phones = set(c.phoneNumber for c in all_contacts if c.phoneNumber)
    already_covered = (email in emails if email else True) and (phone in phones if phone else True)

    # Step 5: If new info, create new secondary contact
    if not already_covered:
        new_secondary = models.Contact(
            email=email,
            phoneNumber=phone,
            linkPrecedence="secondary",
            linkedId=primary_id,
        )
        db.add(new_secondary)
        db.commit()
        db.refresh(new_secondary)
        all_contacts.append(new_secondary)

    # Step 6: Build final response
    primary = next(c for c in all_contacts if c.id == primary_id)
    unique_emails = sorted(set(c.email for c in all_contacts if c.email))
    unique_phones = sorted(set(c.phoneNumber for c in all_contacts if c.phoneNumber))
    secondary_ids = sorted(c.id for c in all_contacts if c.linkPrecedence == "secondary")

    # Ensure primary's email and phone appear first
    if primary.email and primary.email in unique_emails:
        unique_emails.remove(primary.email)
        unique_emails.insert(0, primary.email)
    if primary.phoneNumber and primary.phoneNumber in unique_phones:
        unique_phones.remove(primary.phoneNumber)
        unique_phones.insert(0, primary.phoneNumber)

    return {
        "contact": {
            "primaryContactId": primary_id,
            "emails": unique_emails,
            "phoneNumbers": unique_phones,
            "secondaryContactIds": secondary_ids,
        }
    }
