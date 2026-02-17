from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.enums import NodeType
from app.models import Node
from app.schemas import NodeResponse, NodeCreate, NodeUpdate

router = APIRouter(prefix="/transport-nodes", tags=["Transport Nodes"])

@router.get("", response_model=List[NodeResponse])
def get_transport_nodes(db: Session = Depends(get_db)):
    transport_nodes = db.query(Node).all()
    return transport_nodes

@router.get("/{node_id}", response_model=NodeResponse)
def get_node_by_id(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

@router.post("/", response_model=NodeCreate)
def create_transport_node(node_name, slug: str, latitude: float, longitude: float, node_type: NodeType, db: Session = Depends(get_db)):
    # Checking if following Node already exists
    exists_node = db.query(Node).filter(Node.name == node_name or (Node.latitude == latitude and Node.longitude == longitude)).first()
    if exists_node:
        raise HTTPException(status_code=409, detail="Following node already exists")

    ## slug = slugify(node_name)
    new_node = Node(name=node_name, slug=slug, latitude=latitude, longitude=longitude, node_type=node_type)
    db.add(new_node)
    db.commit()
    db.refresh(new_node)
    return new_node

@router.patch("/{node_id}", response_model=NodeResponse)
def update_node_data(node_id: int, node_data: NodeUpdate, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Checks if Node with same slug already exists
    if node_data.slug is not None:
        node_exists = db.query(Node).filter(Node.slug == node_data.slug).first()
        if node_exists:
            raise HTTPException(status_code=409, detail="Following node already exists")

    # Update fields
    update_node_data = node_data.model_dump(exclude_unset=True)
    for key, value in update_node_data.items():
        setattr(node, key, value)

    db.commit()
    db.refresh(node)
    return node

@router.delete("/{node_id}", response_model=NodeResponse)
def delete_node_by_id(node_id: int, db: Session = Depends(get_db)):
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    db.delete(node)
    db.commit()
    return f"Node: {node.slug} was deleted"
