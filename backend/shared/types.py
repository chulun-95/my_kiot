from sqlalchemy import BigInteger, Integer


PKType = BigInteger().with_variant(Integer(), "sqlite")
FKType = BigInteger().with_variant(Integer(), "sqlite")
