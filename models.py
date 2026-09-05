from sqlalchemy import create_engine, Column, Float, String, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine('sqlite:///mi_base.db', echo=True)

Base = declarative_base()

class Product(Base):
 __tablename__ = 'productos'
 __table_args__ = {'sqlite_autoincrement': True}
 id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
 name = Column(String, nullable=False)
 price = Column(Float, nullable=False)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
#new_product = Product(name="Chicken", price=560.2)
#session.add(new_product)
#session.commit()
