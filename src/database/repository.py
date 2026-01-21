"""
Data access layer for F1 telemetry database.

This module provides high-level functions for storing and retrieving
telemetry data from the database.
"""

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from .connection import get_session, close_session
from .models import (
    Session, Driver, TelemetryFrame, DriverTelemetry,
    TrackStatus, QualifyingResult, QualifyingTelemetry
)


def check_session_exists(year, round_number, session_type):
    """
    Check if a session already exists in the database.
    
    Args:
        year: Year of the session
        round_number: Round number
        session_type: Type of session ('R', 'Q', 'S', 'SQ')
    
    Returns:
        True if session exists, False otherwise
    """
    session = get_session()
    try:
        result = session.query(Session).filter(
            and_(
                Session.year == year,
                Session.round_number == round_number,
                Session.session_type == session_type
            )
        ).first()
        return result is not None
    finally:
        close_session(session)


def save_race_telemetry(year, round_number, session_type, session_info, telemetry_data):
    """
    Save race telemetry data to the database.
    
    Args:
        year: Year of the session
        round_number: Round number
        session_type: Type of session ('R', 'S')
        session_info: Dictionary containing session metadata
        telemetry_data: Dictionary containing frames, driver_colors, track_statuses, total_laps
    
    Returns:
        Session ID if successful, None otherwise
    """
    db_session = get_session()
    
    try:
        # Check if session already exists
        existing_session = db_session.query(Session).filter(
            and_(
                Session.year == year,
                Session.round_number == round_number,
                Session.session_type == session_type
            )
        ).first()
        
        if existing_session:
            print(f"Session already exists in database: {year} Round {round_number} {session_type}")
            return existing_session.id
        
        # Create session record
        session_record = Session(
            year=year,
            round_number=round_number,
            session_type=session_type,
            event_name=session_info.get('event_name', ''),
            circuit_name=session_info.get('circuit_name', ''),
            country=session_info.get('country', ''),
            event_date=session_info.get('date', ''),
            total_laps=telemetry_data.get('total_laps', 0),
            circuit_rotation=session_info.get('circuit_rotation', 0.0)
        )
        db_session.add(session_record)
        db_session.flush()  # Get session ID
        
        # Create driver records
        driver_colors = telemetry_data.get('driver_colors', {})
        driver_map = {}  # Map driver code to driver record
        
        # Extract unique drivers from frames
        frames = telemetry_data.get('frames', [])
        if frames:
            first_frame = frames[0]
            for driver_code in first_frame.get('drivers', {}).keys():
                color = driver_colors.get(driver_code, (128, 128, 128))
                driver_record = Driver(
                    session_id=session_record.id,
                    driver_code=driver_code,
                    color_r=color[0],
                    color_g=color[1],
                    color_b=color[2]
                )
                db_session.add(driver_record)
                db_session.flush()
                driver_map[driver_code] = driver_record
        
        # Save track statuses
        for status_data in telemetry_data.get('track_statuses', []):
            track_status = TrackStatus(
                session_id=session_record.id,
                status=status_data['status'],
                start_time=status_data['start_time'],
                end_time=status_data.get('end_time')
            )
            db_session.add(track_status)
        
        # Save telemetry frames in batches for better performance
        print(f"Saving {len(frames)} telemetry frames to database...")
        batch_size = 100
        
        for i in range(0, len(frames), batch_size):
            batch_frames = frames[i:i + batch_size]
            
            for frame_data in batch_frames:
                # Create frame record
                weather = frame_data.get('weather', {})
                frame_record = TelemetryFrame(
                    session_id=session_record.id,
                    time=frame_data['t'],
                    lap=frame_data.get('lap'),
                    track_temp=weather.get('track_temp'),
                    air_temp=weather.get('air_temp'),
                    humidity=weather.get('humidity'),
                    wind_speed=weather.get('wind_speed'),
                    wind_direction=weather.get('wind_direction'),
                    rain_state=weather.get('rain_state')
                )
                db_session.add(frame_record)
                db_session.flush()
                
                # Create driver telemetry records for this frame
                for driver_code, driver_data in frame_data.get('drivers', {}).items():
                    if driver_code in driver_map:
                        telemetry_record = DriverTelemetry(
                            frame_id=frame_record.id,
                            driver_id=driver_map[driver_code].id,
                            x=driver_data['x'],
                            y=driver_data['y'],
                            distance=driver_data.get('dist'),
                            relative_distance=driver_data.get('rel_dist'),
                            position=driver_data.get('position'),
                            lap=driver_data.get('lap'),
                            speed=driver_data.get('speed'),
                            gear=driver_data.get('gear'),
                            drs=driver_data.get('drs'),
                            throttle=driver_data.get('throttle'),
                            brake=driver_data.get('brake'),
                            tyre_compound=int(driver_data.get('tyre', 0))
                        )
                        db_session.add(telemetry_record)
            
            # Commit batch
            db_session.commit()
            if (i + batch_size) % 500 == 0:
                print(f"  Saved {min(i + batch_size, len(frames))}/{len(frames)} frames...")
        
        print(f"Successfully saved race telemetry to database!")
        return session_record.id
        
    except Exception as e:
        db_session.rollback()
        print(f"Error saving race telemetry to database: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_session(db_session)


def load_race_telemetry(year, round_number, session_type):
    """
    Load race telemetry data from the database.
    
    Args:
        year: Year of the session
        round_number: Round number
        session_type: Type of session ('R', 'S')
    
    Returns:
        Dictionary containing frames, driver_colors, track_statuses, total_laps
        or None if not found
    """
    db_session = get_session()
    
    try:
        # Find session
        session_record = db_session.query(Session).filter(
            and_(
                Session.year == year,
                Session.round_number == round_number,
                Session.session_type == session_type
            )
        ).first()
        
        if not session_record:
            return None
        
        print(f"Loading race telemetry from database for {session_record.event_name}...")
        
        # Load driver colors
        driver_colors = {}
        drivers = db_session.query(Driver).filter(Driver.session_id == session_record.id).all()
        driver_id_to_code = {}
        
        for driver in drivers:
            driver_colors[driver.driver_code] = (driver.color_r, driver.color_g, driver.color_b)
            driver_id_to_code[driver.id] = driver.driver_code
        
        # Load track statuses
        track_statuses = []
        statuses = db_session.query(TrackStatus).filter(
            TrackStatus.session_id == session_record.id
        ).order_by(TrackStatus.start_time).all()
        
        for status in statuses:
            track_statuses.append({
                'status': status.status,
                'start_time': status.start_time,
                'end_time': status.end_time
            })
        
        # Load telemetry frames
        frames = []
        frame_records = db_session.query(TelemetryFrame).filter(
            TelemetryFrame.session_id == session_record.id
        ).order_by(TelemetryFrame.time).all()
        
        print(f"Loading {len(frame_records)} frames from database...")
        
        for frame_record in frame_records:
            # Build weather data
            weather = {}
            if frame_record.track_temp is not None:
                weather = {
                    'track_temp': frame_record.track_temp,
                    'air_temp': frame_record.air_temp,
                    'humidity': frame_record.humidity,
                    'wind_speed': frame_record.wind_speed,
                    'wind_direction': frame_record.wind_direction,
                    'rain_state': frame_record.rain_state
                }
            
            # Load driver telemetry for this frame
            drivers_data = {}
            telemetry_points = db_session.query(DriverTelemetry).filter(
                DriverTelemetry.frame_id == frame_record.id
            ).all()
            
            for point in telemetry_points:
                driver_code = driver_id_to_code.get(point.driver_id)
                if driver_code:
                    drivers_data[driver_code] = {
                        'x': point.x,
                        'y': point.y,
                        'dist': point.distance,
                        'rel_dist': point.relative_distance,
                        'position': point.position,
                        'lap': point.lap,
                        'speed': point.speed,
                        'gear': point.gear,
                        'drs': point.drs,
                        'throttle': point.throttle,
                        'brake': point.brake,
                        'tyre': float(point.tyre_compound)
                    }
            
            frame_data = {
                't': frame_record.time,
                'lap': frame_record.lap,
                'drivers': drivers_data
            }
            
            if weather:
                frame_data['weather'] = weather
            
            frames.append(frame_data)
        
        print(f"Successfully loaded race telemetry from database!")
        
        return {
            'frames': frames,
            'driver_colors': driver_colors,
            'track_statuses': track_statuses,
            'total_laps': session_record.total_laps
        }
        
    except Exception as e:
        print(f"Error loading race telemetry from database: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_session(db_session)


def save_qualifying_telemetry(year, round_number, session_type, session_info, quali_data):
    """
    Save qualifying telemetry data to the database.
    
    Args:
        year: Year of the session
        round_number: Round number
        session_type: Type of session ('Q', 'SQ')
        session_info: Dictionary containing session metadata
        quali_data: Dictionary containing results, telemetry, max_speed, min_speed
    
    Returns:
        Session ID if successful, None otherwise
    """
    db_session = get_session()
    
    try:
        # Check if session already exists
        existing_session = db_session.query(Session).filter(
            and_(
                Session.year == year,
                Session.round_number == round_number,
                Session.session_type == session_type
            )
        ).first()
        
        if existing_session:
            print(f"Qualifying session already exists in database: {year} Round {round_number} {session_type}")
            return existing_session.id
        
        # Create session record
        session_record = Session(
            year=year,
            round_number=round_number,
            session_type=session_type,
            event_name=session_info.get('event_name', ''),
            circuit_name=session_info.get('circuit_name', ''),
            country=session_info.get('country', ''),
            event_date=session_info.get('date', '')
        )
        db_session.add(session_record)
        db_session.flush()
        
        # Create driver records and qualifying results
        driver_map = {}
        
        for result_data in quali_data.get('results', []):
            driver_code = result_data['code']
            color = result_data.get('color', (128, 128, 128))
            
            # Create driver record
            driver_record = Driver(
                session_id=session_record.id,
                driver_code=driver_code,
                full_name=result_data.get('full_name'),
                color_r=color[0],
                color_g=color[1],
                color_b=color[2]
            )
            db_session.add(driver_record)
            db_session.flush()
            driver_map[driver_code] = driver_record
            
            # Create qualifying result record
            quali_result = QualifyingResult(
                session_id=session_record.id,
                driver_id=driver_record.id,
                position=result_data['position'],
                q1_time=float(result_data['Q1']) if result_data.get('Q1') else None,
                q2_time=float(result_data['Q2']) if result_data.get('Q2') else None,
                q3_time=float(result_data['Q3']) if result_data.get('Q3') else None
            )
            db_session.add(quali_result)
            db_session.flush()
            
            # Save telemetry data for each segment
            telemetry = quali_data.get('telemetry', {}).get(driver_code, {})
            
            for segment in ['Q1', 'Q2', 'Q3']:
                segment_data = telemetry.get(segment, {})
                frames = segment_data.get('frames', [])
                
                if frames:
                    quali_telemetry = QualifyingTelemetry(
                        result_id=quali_result.id,
                        segment=segment,
                        frames_json=frames,
                        max_speed=segment_data.get('max_speed'),
                        min_speed=segment_data.get('min_speed'),
                        sector1_time=segment_data.get('sector_times', {}).get('sector1'),
                        sector2_time=segment_data.get('sector_times', {}).get('sector2'),
                        sector3_time=segment_data.get('sector_times', {}).get('sector3'),
                        compound=segment_data.get('compound'),
                        drs_zones_json=segment_data.get('drs_zones', [])
                    )
                    db_session.add(quali_telemetry)
        
        db_session.commit()
        print(f"Successfully saved qualifying telemetry to database!")
        return session_record.id
        
    except Exception as e:
        db_session.rollback()
        print(f"Error saving qualifying telemetry to database: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_session(db_session)


def load_qualifying_telemetry(year, round_number, session_type):
    """
    Load qualifying telemetry data from the database.
    
    Args:
        year: Year of the session
        round_number: Round number
        session_type: Type of session ('Q', 'SQ')
    
    Returns:
        Dictionary containing results, telemetry, max_speed, min_speed
        or None if not found
    """
    db_session = get_session()
    
    try:
        # Find session
        session_record = db_session.query(Session).filter(
            and_(
                Session.year == year,
                Session.round_number == round_number,
                Session.session_type == session_type
            )
        ).first()
        
        if not session_record:
            return None
        
        print(f"Loading qualifying telemetry from database for {session_record.event_name}...")
        
        # Load qualifying results
        results = []
        quali_results = db_session.query(QualifyingResult).filter(
            QualifyingResult.session_id == session_record.id
        ).order_by(QualifyingResult.position).all()
        
        # Load telemetry data
        telemetry = {}
        max_speed = 0.0
        min_speed = 0.0
        
        for result in quali_results:
            driver = result.driver
            
            # Build result data
            results.append({
                'code': driver.driver_code,
                'full_name': driver.full_name,
                'position': result.position,
                'color': (driver.color_r, driver.color_g, driver.color_b),
                'Q1': str(result.q1_time) if result.q1_time else None,
                'Q2': str(result.q2_time) if result.q2_time else None,
                'Q3': str(result.q3_time) if result.q3_time else None
            })
            
            # Build telemetry data
            driver_telemetry = {'full_name': driver.full_name}
            
            for segment_telemetry in result.telemetry_data:
                segment = segment_telemetry.segment
                driver_telemetry[segment] = {
                    'frames': segment_telemetry.frames_json,
                    'track_statuses': [],  # Not stored separately for qualifying
                    'drs_zones': segment_telemetry.drs_zones_json or [],
                    'max_speed': segment_telemetry.max_speed,
                    'min_speed': segment_telemetry.min_speed,
                    'sector_times': {
                        'sector1': segment_telemetry.sector1_time,
                        'sector2': segment_telemetry.sector2_time,
                        'sector3': segment_telemetry.sector3_time
                    },
                    'compound': segment_telemetry.compound
                }
                
                # Update global max/min speeds
                if segment_telemetry.max_speed and segment_telemetry.max_speed > max_speed:
                    max_speed = segment_telemetry.max_speed
                if segment_telemetry.min_speed and (segment_telemetry.min_speed < min_speed or min_speed == 0.0):
                    min_speed = segment_telemetry.min_speed
            
            telemetry[driver.driver_code] = driver_telemetry
        
        print(f"Successfully loaded qualifying telemetry from database!")
        
        return {
            'results': results,
            'telemetry': telemetry,
            'max_speed': max_speed,
            'min_speed': min_speed
        }
        
    except Exception as e:
        print(f"Error loading qualifying telemetry from database: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        close_session(db_session)


def get_all_sessions():
    """
    Get all sessions stored in the database.
    
    Returns:
        List of session dictionaries
    """
    db_session = get_session()
    
    try:
        sessions = db_session.query(Session).order_by(Session.year.desc(), Session.round_number.desc()).all()
        
        result = []
        for session in sessions:
            result.append({
                'year': session.year,
                'round': session.round_number,
                'session_type': session.session_type,
                'event_name': session.event_name,
                'country': session.country,
                'date': session.event_date
            })
        
        return result
        
    finally:
        close_session(db_session)
