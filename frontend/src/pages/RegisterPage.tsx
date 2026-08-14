import AuthShell from '../components/AuthShell';
import AuthFlipCard from '../components/AuthFlipCard';

const RegisterPage = () => (
    <AuthShell>
        <AuthFlipCard initialSide="register" />
    </AuthShell>
);

export default RegisterPage;
