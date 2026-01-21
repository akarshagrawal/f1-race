"""
SQLAlchemy ORM models for F1 telemetry database.

This module defines the database schema for storing F1 race and qualifying
session data, including telemetry, driver information, and track statuses.
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Session(Base):
    """Represents an F1 session (race, qualifying, sprint, etc.)"""
    __tablename__ = 'sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    round_number = Column(Integer, nullable=False)
    session_type = Column(String(10), nullable=False)  # 'R', 'Q', 'S', 'SQ'
    event_name = Column(String(100), nullable=False)
    circuit_name = Column(String(100))
    country = Column(String(50))
    event_date = Column(String(20))
    total_laps = Column(Integer)
    circuit_rotation = Column(Float)
    
    # Relationships
    drivers = relationship("Driver", back_populates="session", cascade="all, delete-orphan")
    telemetry_frames = relationship("TelemetryFrame", back_populates="session", cascade="all, delete-orphan")
    track_statuses = relationship("TrackStatus", back_populates="session", cascade="all, delete-orphan")
    qualifying_results = relationship("QualifyingResult", back_populates="session", cascade="all, delete-orphan")
    
    # Unique constraint on year, round, and session type
    __table_args__ = (
        Index('idx_session_lookup', 'year', 'round_number', 'session_type', unique=True),
    )
    
    def __repr__(self):
        return f"<Session(year={self.year}, round={self.round_number}, type={self.session_type}, event={self.event_name})>"


class Driver(Base):
    """Represents a driver in a specific session"""
    __tablename__ = 'drivers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    driver_code = Column(String(3), nullable=False)  # e.g., 'VER', 'HAM'
    driver_number = Column(Integer)
    full_name = Column(String(100))
    team = Column(String(50))
    color_r = Column(Integer)  # RGB color for visualization
    color_g = Column(Integer)
    color_b = Column(Integer)
    
    # Relationships
    session = relationship("Session", back_populates="drivers")
    telemetry_points = relationship("DriverTelemetry", back_populates="driver", cascade="all, delete-orphan")
    qualifying_results = relationship("QualifyingResult", back_populates="driver", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_driver_session', 'session_id', 'driver_code'),
    )
    
    def __repr__(self):
        return f"<Driver(code={self.driver_code}, name={self.full_name})>"


class TelemetryFrame(Base):
    """Represents a single frame/timestamp in the race replay"""
    __tablename__ = 'telemetry_frames'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    time = Column(Float, nullable=False)  # Time in seconds from race start
    lap = Column(Integer)  # Leader's lap number at this time
    
    # Weather data (optional)
    track_temp = Column(Float)
    air_temp = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(Float)
    rain_state = Column(String(20))  # 'DRY', 'RAINING'
    
    # Relationships
    session = relationship("Session", back_populates="telemetry_frames")
    driver_data = relationship("DriverTelemetry", back_populates="frame", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_frame_session_time', 'session_id', 'time'),
    )
    
    def __repr__(self):
        return f"<TelemetryFrame(session_id={self.session_id}, time={self.time}, lap={self.lap})>"


class DriverTelemetry(Base):
    """Represents telemetry data for a specific driver at a specific frame"""
    __tablename__ = 'driver_telemetry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    frame_id = Column(Integer, ForeignKey('telemetry_frames.id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    
    # Position data
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    distance = Column(Float)  # Total race distance
    relative_distance = Column(Float)  # Relative distance on track (0-1)
    position = Column(Integer)  # Race position (1-20)
    lap = Column(Integer)  # Driver's current lap
    
    # Telemetry data
    speed = Column(Float)  # Speed in km/h
    gear = Column(Integer)
    drs = Column(Integer)  # DRS status
    throttle = Column(Float)  # Throttle percentage (0-100)
    brake = Column(Float)  # Brake pressure
    tyre_compound = Column(Integer)  # Tire compound as integer
    
    # Relationships
    frame = relationship("TelemetryFrame", back_populates="driver_data")
    driver = relationship("Driver", back_populates="telemetry_points")
    
    __table_args__ = (
        Index('idx_telemetry_frame_driver', 'frame_id', 'driver_id'),
    )
    
    def __repr__(self):
        return f"<DriverTelemetry(driver_id={self.driver_id}, frame_id={self.frame_id}, pos={self.position})>"


class TrackStatus(Base):
    """Represents track status changes (safety car, VSC, etc.)"""
    __tablename__ = 'track_statuses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    status = Column(String(10), nullable=False)  # Status code
    start_time = Column(Float, nullable=False)  # Start time in seconds
    end_time = Column(Float)  # End time in seconds (None if ongoing)
    
    # Relationships
    session = relationship("Session", back_populates="track_statuses")
    
    __table_args__ = (
        Index('idx_track_status_session', 'session_id', 'start_time'),
    )
    
    def __repr__(self):
        return f"<TrackStatus(session_id={self.session_id}, status={self.status}, start={self.start_time})>"


class QualifyingResult(Base):
    """Represents qualifying results for a driver"""
    __tablename__ = 'qualifying_results'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    driver_id = Column(Integer, ForeignKey('drivers.id'), nullable=False)
    position = Column(Integer, nullable=False)
    q1_time = Column(Float)  # Q1 lap time in seconds
    q2_time = Column(Float)  # Q2 lap time in seconds
    q3_time = Column(Float)  # Q3 lap time in seconds
    
    # Relationships
    session = relationship("Session", back_populates="qualifying_results")
    driver = relationship("Driver", back_populates="qualifying_results")
    telemetry_data = relationship("QualifyingTelemetry", back_populates="result", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_quali_result_session', 'session_id', 'position'),
    )
    
    def __repr__(self):
        return f"<QualifyingResult(driver_id={self.driver_id}, position={self.position})>"


class QualifyingTelemetry(Base):
    """Represents telemetry data for qualifying laps"""
    __tablename__ = 'qualifying_telemetry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    result_id = Column(Integer, ForeignKey('qualifying_results.id'), nullable=False)
    segment = Column(String(2), nullable=False)  # 'Q1', 'Q2', 'Q3'
    
    # Store telemetry frames as JSON for qualifying (more flexible)
    # Each frame contains: t, x, y, dist, rel_dist, speed, gear, throttle, brake, drs
    frames_json = Column(JSON, nullable=False)
    
    # Additional metadata
    max_speed = Column(Float)
    min_speed = Column(Float)
    sector1_time = Column(Float)
    sector2_time = Column(Float)
    sector3_time = Column(Float)
    compound = Column(Integer)  # Tire compound
    drs_zones_json = Column(JSON)  # DRS zone data as JSON
    
    # Relationships
    result = relationship("QualifyingResult", back_populates="telemetry_data")
    
    __table_args__ = (
        Index('idx_quali_telemetry_result', 'result_id', 'segment'),
    )
    
    def __repr__(self):
        return f"<QualifyingTelemetry(result_id={self.result_id}, segment={self.segment})>"
