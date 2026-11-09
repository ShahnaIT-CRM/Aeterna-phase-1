// [value, label] pairs. Values match the Django TextChoices on the backend.
export const EMPLOYMENT_TYPES = [['full_time', 'Full-Time'], ['part_time', 'Part-Time'], ['contract', 'Contract'], ['freelance', 'Freelance / Visiting'], ['adhoc', 'Adhoc']]
export const WORK_MODES = [['onsite', 'Onsite'], ['hybrid', 'Hybrid / Guest Lecturer'], ['remote', 'Remote']]
export const INSTITUTE_TYPES = [['preschool', 'Pre-School / Nursery'], ['primary', 'Primary School (Grades 1-5)'], ['secondary', 'Secondary School (Grades 6-10)'], ['senior_secondary', 'Senior Secondary School (Grades 11-12)'], ['undergrad', 'Undergraduate College'], ['postgrad', 'Postgraduate College / University'], ['deemed_university', 'Deemed University'], ['coaching', 'Coaching Institute / Test Prep'], ['edtech', 'Ed-Tech / Online Teaching'], ['vocational', 'Vocational Training Institute'], ['special_ed', 'Special Education School']]
export const QUAL_LEVELS = [['high_school', 'High School (10th)'], ['intermediate', 'Intermediate (12th)'], ['diploma', 'Diploma'], ['bachelors', "Bachelor's Degree"], ['masters', "Master's Degree"], ['mphil', 'M.Phil.'], ['phd', 'Ph.D. / Doctorate'], ['pg_diploma', 'PG Diploma'], ['certificate', 'Certificate'], ['integrated', 'Integrated Degree']]
export const COURSE_TYPES = [['full_time', 'Full Time'], ['part_time', 'Part Time'], ['distance', 'Distance / Correspondence']]
export const GRADING = [['percentage', 'Percentage'], ['cgpa', 'CGPA'], ['grade', 'Grade']]
export const GENDERS = [['male', 'Male'], ['female', 'Female'], ['other', 'Other'], ['prefer_not', 'Prefer not to say']]
export const WORK_STATUS = [['employed', 'Employed (not looking)'], ['open', 'Open to opportunities'], ['active', 'Actively looking']]
export const VISIBILITY = [['public', 'Public'], ['selective', 'Selective'], ['private', 'Private']]
export const NOTICE = [['7', '7 days'], ['15', '15 days'], ['30', '30 days'], ['60', '2 months']]
export const SALARY_DISPLAY = [['range', 'Show salary range'], ['industry', 'As per industry standards']]
export const JOB_STATUS = [['open', 'Open'], ['draft', 'Draft'], ['closed', 'Closed']]
export const APP_STATUS = [['applied', 'Applied'], ['viewed', 'Viewed'], ['shortlisted', 'Shortlisted'], ['interview', 'Interview scheduled'], ['rejected', 'Rejected'], ['offered', 'Offer letter sent'], ['hired', 'Hired'], ['bookmarked', 'Bookmarked for later']]
export const BOARDS = ['CBSE', 'CISCE (ICSE/ISC)', 'IB', 'IGCSE / Cambridge', 'NIOS', 'State Board', 'Other']
export const DESIGNATIONS = ['PGT', 'TGT', 'PRT', 'Assistant Professor', 'Associate Professor', 'Professor', 'HOD', 'Principal', 'Vice Principal', 'Academic Coordinator', 'Tutor', 'Guest Faculty', 'Special Educator', 'Lab Assistant']

export const label = (list, v) => list.find(([k]) => k === v)?.[1] ?? v
export const money = (n) => (n == null || n === '' ? '' : '₹' + Number(n).toLocaleString('en-IN'))
export const WORK_STATUS_STYLE = { employed: 'bg-blue-100 text-blue-900', open: 'bg-orange-100 text-orange-900', active: 'bg-green-100 text-green-900' }
export const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString('en-IN', { dateStyle: 'full', timeStyle: 'short' }) : '')
